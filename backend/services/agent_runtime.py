from __future__ import annotations

from collections.abc import Iterator
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from integrations.deepseek import DeepSeekError, create_chat_model
from retrieval.models import RetrievalSource
from services.agent_identity import (
    AgentPublicProfile,
    build_public_profile,
    render_public_profile_answer,
    requires_public_profile_answer,
)
from services.agent_strategy import RuntimeStrategy, decide_strategy
from services.retrieval import (
    build_knowledge_overview_context,
    build_no_knowledge_answer,
    build_no_match_answer,
    build_retrieval_context,
    execute_knowledge_operation,
    has_ready_knowledge,
    has_knowledge_scope,
)
from services.agent_prompt_policies import platform_identity_policy, response_policy


class ModelMessage(TypedDict):
    role: str
    content: str


class AnswerStreamInput(TypedDict):
    system_prompt: str | None
    history: list[ModelMessage]
    content: str
    retrieval_context: str | None
    strategy: RuntimeStrategy
    public_profile: AgentPublicProfile


class AgentWorkflowState(TypedDict):
    user_id: str
    agent_id: str
    agent_kind: str
    system_prompt: str | None
    history: list[ModelMessage]
    content: str
    use_knowledge_base: bool
    knowledge_enabled: bool
    has_bound_scope: bool
    has_ready_knowledge: bool
    direct_answer_reason: str
    retrieval_failed: bool
    public_profile: AgentPublicProfile
    public_answer: str
    strategy: RuntimeStrategy
    sources: list[RetrievalSource]
    answer: str
    stream_input: AnswerStreamInput | None


RouteName = Literal["answer_public_profile", "direct_model_answer", "execute_knowledge_operation", "generate_answer", "knowledge_unavailable", "no_match", "retrieval_failed"]


def stream_answer(
    system_prompt: str | None,
    history: list[ModelMessage],
    content: str,
    retrieval_context: str | None = None,
    strategy: RuntimeStrategy | None = None,
    public_profile: AgentPublicProfile | None = None,
) -> Iterator[str]:
    messages: list[BaseMessage] = []
    if system_prompt and system_prompt.strip():
        messages.append(SystemMessage(content=system_prompt.strip()))
    if retrieval_context:
        messages.append(SystemMessage(content=retrieval_context))
    messages.append(SystemMessage(content=platform_identity_policy(public_profile)))
    messages.append(SystemMessage(content=response_policy(strategy or RuntimeStrategy("direct_answer", False))))
    messages.extend(_history_messages(history[-10:]))
    messages.append(HumanMessage(content=content))
    try:
        for response_chunk in create_chat_model().stream(messages):
            text = _message_text(response_chunk.content)
            if text:
                yield text
    except Exception as error:
        raise DeepSeekError("DeepSeek response is unavailable") from error


def stream_with_retrieval(
    user_id: str,
    agent_id: str,
    agent_kind: str,
    system_prompt: str | None,
    history: list[ModelMessage],
    content: str,
    use_knowledge_base: bool,
    agent_name: str | None = None,
    agent_description: str | None = None,
) -> Iterator[dict[str, object]]:
    initial_state: AgentWorkflowState = {
        "user_id": user_id,
        "agent_id": agent_id,
        "agent_kind": agent_kind,
        "system_prompt": system_prompt,
        "history": history,
        "content": content,
        "use_knowledge_base": use_knowledge_base,
        "knowledge_enabled": False,
        "has_bound_scope": False,
        "has_ready_knowledge": False,
        "direct_answer_reason": "",
        "retrieval_failed": False,
        "public_profile": build_public_profile(agent_name, agent_description, agent_kind == "personal" or use_knowledge_base),
        "public_answer": "",
        "strategy": RuntimeStrategy("direct_answer", False),
        "sources": [],
        "answer": "",
        "stream_input": None,
    }
    yield {"type": "status", "stage": "analyzing", "text": "正在分析问题"}
    for update in _build_agent_graph().stream(initial_state, stream_mode="updates"):
        for node_name, result in update.items():
            yield from _events_for_node(node_name, result)


def _build_agent_graph():
    graph = StateGraph(AgentWorkflowState)
    graph.add_node("check_knowledge_capability", _check_knowledge_capability)
    graph.add_node("direct_model_answer", _direct_model_answer)
    graph.add_node("analyze_request", _analyze_request)
    graph.add_node("answer_public_profile", _answer_public_profile)
    graph.add_node("execute_knowledge_operation", _execute_knowledge_operation)
    graph.add_node("evaluate_evidence", _evaluate_evidence)
    graph.add_node("knowledge_unavailable", _knowledge_unavailable)
    graph.add_node("no_match", _no_match)
    graph.add_node("retrieval_failed", _retrieval_failed)
    graph.add_node("generate_answer", _generate_answer)
    graph.add_node("guard_identity", _guard_identity)
    graph.add_edge(START, "guard_identity")
    graph.add_conditional_edges("guard_identity", _route_after_identity_guard, {
        "answer_public_profile": "answer_public_profile", "check_knowledge_capability": "check_knowledge_capability",
    })
    graph.add_edge("answer_public_profile", END)
    graph.add_conditional_edges("check_knowledge_capability", _route_after_knowledge_check, {
        "direct_model_answer": "direct_model_answer", "analyze_request": "analyze_request", "knowledge_unavailable": "knowledge_unavailable",
    })
    graph.add_edge("direct_model_answer", "generate_answer")
    graph.add_edge("knowledge_unavailable", END)
    graph.add_conditional_edges("analyze_request", _route_after_analysis, {
        "execute_knowledge_operation": "execute_knowledge_operation", "generate_answer": "generate_answer",
    })
    graph.add_conditional_edges("execute_knowledge_operation", _route_after_knowledge_operation, {
        "generate_answer": "generate_answer", "evaluate_evidence": "evaluate_evidence",
    })
    graph.add_conditional_edges("evaluate_evidence", _route_after_evidence, {
        "generate_answer": "generate_answer", "no_match": "no_match", "retrieval_failed": "retrieval_failed",
    })
    graph.add_edge("no_match", END)
    graph.add_edge("retrieval_failed", END)
    graph.add_edge("generate_answer", END)
    return graph.compile()


def _analyze_request(state: AgentWorkflowState) -> dict[str, RuntimeStrategy]:
    return {"strategy": decide_strategy(state["content"], state["history"], state["knowledge_enabled"])}


def _check_knowledge_capability(state: AgentWorkflowState) -> dict[str, bool]:
    if state["agent_kind"] == "builtin":
        knowledge_enabled = state["use_knowledge_base"]
        return {"knowledge_enabled": knowledge_enabled, "has_bound_scope": False, "has_ready_knowledge": has_ready_knowledge(state["user_id"], state["agent_id"]) if knowledge_enabled else False}
    has_bound_scope = has_knowledge_scope(state["user_id"], state["agent_id"])
    return {
        "knowledge_enabled": has_bound_scope,
        "has_bound_scope": has_bound_scope,
        "has_ready_knowledge": has_ready_knowledge(state["user_id"], state["agent_id"]) if has_bound_scope else False,
    }


def _direct_model_answer(state: AgentWorkflowState) -> dict[str, str]:
    if state["agent_kind"] == "personal" and not state["has_bound_scope"]:
        return {"direct_answer_reason": "unbound_personal_scope"}
    return {"direct_answer_reason": "knowledge_disabled"}


def _guard_identity(state: AgentWorkflowState) -> dict[str, str]:
    if requires_public_profile_answer(state["content"]):
        return {"public_answer": render_public_profile_answer(state["public_profile"], state["content"])}
    return {"public_answer": ""}


def _route_after_identity_guard(state: AgentWorkflowState) -> Literal["answer_public_profile", "check_knowledge_capability"]:
    return "answer_public_profile" if state["public_answer"] else "check_knowledge_capability"


def _route_after_knowledge_check(state: AgentWorkflowState) -> Literal["direct_model_answer", "analyze_request", "knowledge_unavailable"]:
    if not state["knowledge_enabled"]:
        return "direct_model_answer"
    if not state["has_ready_knowledge"]:
        return "knowledge_unavailable"
    return "analyze_request"


def _answer_public_profile(state: AgentWorkflowState) -> dict[str, str]:
    return {"answer": state["public_answer"]}


def _knowledge_unavailable(_: AgentWorkflowState) -> dict[str, str]:
    return {"answer": build_no_knowledge_answer()}


def _route_after_analysis(state: AgentWorkflowState) -> RouteName:
    if state["strategy"].uses_knowledge:
        return "execute_knowledge_operation"
    return "generate_answer"


def _execute_knowledge_operation(state: AgentWorkflowState) -> dict[str, object]:
    try:
        return {"sources": execute_knowledge_operation(
            state["strategy"].knowledge_operation, state["user_id"], state["agent_id"], state["content"],
        ), "retrieval_failed": False}
    except Exception:
        return {"sources": [], "retrieval_failed": True}


def _route_after_knowledge_operation(state: AgentWorkflowState) -> Literal["generate_answer", "evaluate_evidence"]:
    if state["strategy"].knowledge_operation == "knowledge_overview" and state["sources"]:
        return "generate_answer"
    return "evaluate_evidence"


def _evaluate_evidence(state: AgentWorkflowState) -> dict[str, RuntimeStrategy]:
    if state["sources"]:
        return {"strategy": state["strategy"]}
    return {"strategy": state["strategy"]}


def _route_after_evidence(state: AgentWorkflowState) -> Literal["generate_answer", "no_match", "retrieval_failed"]:
    if state["retrieval_failed"]:
        return "retrieval_failed"
    return "generate_answer" if state["sources"] else "no_match"


def _no_match(_: AgentWorkflowState) -> dict[str, str]:
    return {"answer": build_no_match_answer()}


def _retrieval_failed(_: AgentWorkflowState) -> dict[str, str]:
    return {"answer": "知识库检索服务暂时不可用，请稍后重试。"}


def _generate_answer(state: AgentWorkflowState) -> dict[str, object]:
    if state["strategy"].knowledge_operation == "knowledge_overview":
        context = build_knowledge_overview_context(state["sources"])
    else:
        context = build_retrieval_context(state["sources"]) if state["strategy"].uses_knowledge else None
    return {"stream_input": {
        "system_prompt": state["system_prompt"],
        "history": state["history"],
        "content": state["content"],
        "retrieval_context": context,
        "strategy": state["strategy"],
        "public_profile": state["public_profile"],
    }}


def _events_for_node(node_name: str, result: dict[str, object]) -> Iterator[dict[str, object]]:
    if node_name == "answer_public_profile":
        answer = result.get("answer")
        if isinstance(answer, str) and answer:
            yield {"type": "answer_delta", "content": answer}
        return
    if node_name == "analyze_request":
        strategy = result["strategy"]
        if isinstance(strategy, RuntimeStrategy):
            if strategy.uses_knowledge:
                text = "正在整理知识库概览" if strategy.knowledge_operation == "knowledge_overview" else "正在检索资料"
                yield {"type": "status", "stage": "retrieving", "text": text}
            else:
                yield {"type": "status", "stage": "generating", "text": "正在生成回答"}
        return
    if node_name == "direct_model_answer":
        if result.get("direct_answer_reason") == "unbound_personal_scope":
            yield {"type": "status", "stage": "generating", "text": "当前智能体未绑定知识库，正在由模型直接回答"}
        return
    if node_name == "knowledge_unavailable":
        yield {"type": "status", "stage": "no_documents", "text": "当前资料范围没有已完成索引的文件"}
        answer = result.get("answer")
        if isinstance(answer, str):
            yield {"type": "answer_delta", "content": answer}
        return
    if node_name == "execute_knowledge_operation":
        if result.get("retrieval_failed") is True:
            return
        sources = result.get("sources", [])
        if isinstance(sources, list) and sources:
            citations = [source.to_citation() for source in sources if isinstance(source, RetrievalSource)]
            document_count = len({source.document_node_id for source in sources if isinstance(source, RetrievalSource)})
            yield {"type": "status", "stage": "context", "text": f"已读取 {document_count} 份资料、{len(citations)} 个片段，正在构造回答上下文"}
            yield {"type": "sources", "items": citations}
        else:
            yield {"type": "status", "stage": "no_match", "text": "未命中已启用的知识库资料"}
        return
    if node_name == "evaluate_evidence":
        return
    if node_name == "no_match":
        answer = result.get("answer")
        if isinstance(answer, str):
            yield {"type": "answer_delta", "content": answer}
        return
    if node_name == "retrieval_failed":
        yield {"type": "status", "stage": "retrieval_failed", "text": "知识库检索服务暂时不可用"}
        answer = result.get("answer")
        if isinstance(answer, str):
            yield {"type": "answer_delta", "content": answer}
        return
    if node_name == "generate_answer":
        answer = result.get("answer")
        if isinstance(answer, str) and answer:
            yield {"type": "answer_delta", "content": answer}
            return
        stream_input = result.get("stream_input")
        if isinstance(stream_input, dict):
            yield {"type": "status", "stage": "generating", "text": "正在生成回答"}
            yield from (
                {"type": "answer_delta", "content": text}
                for text in stream_answer(
                    stream_input["system_prompt"], stream_input["history"], stream_input["content"],
                    stream_input["retrieval_context"], stream_input["strategy"], stream_input["public_profile"],
                )
            )


def _history_messages(history: list[ModelMessage]) -> list[BaseMessage]:
    return [HumanMessage(content=item["content"]) if item["role"] == "user" else AIMessage(content=item["content"]) for item in history]


def _message_text(content: str | list[str | dict[str, object]]) -> str:
    if isinstance(content, str):
        return content
    return "".join(item for item in content if isinstance(item, str))
