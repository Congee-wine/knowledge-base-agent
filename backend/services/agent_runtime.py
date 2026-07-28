from __future__ import annotations

from collections.abc import Iterator
from typing import TypedDict

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from integrations.deepseek import DeepSeekError, create_chat_model
from services.retrieval import build_retrieval_context, retrieve_for_agent


class ModelMessage(TypedDict):
    role: str
    content: str


class RuntimeState(TypedDict):
    content: str
    history: list[ModelMessage]
    messages: list[BaseMessage]
    system_prompt: str | None
    retrieval_context: str | None


def stream_answer(
    system_prompt: str | None, history: list[ModelMessage], content: str, retrieval_context: str | None = None,
) -> Iterator[str]:
    graph = _build_runtime_graph()
    try:
        for message, metadata in graph.stream(
            {"content": content, "history": history, "messages": [], "system_prompt": system_prompt, "retrieval_context": retrieval_context},
            stream_mode="messages",
        ):
            if metadata.get("langgraph_node") != "model":
                continue
            if isinstance(message, (AIMessage, AIMessageChunk)):
                text = _message_text(message.content)
                if text:
                    yield text
    except Exception as error:  # LangChain provider errors have multiple concrete types.
        raise DeepSeekError("DeepSeek response is unavailable") from error


def stream_with_retrieval(user_id: str, agent_id: str, agent_kind: str, system_prompt: str | None, history: list[ModelMessage], content: str, use_knowledge_base: bool) -> Iterator[dict[str, object]]:
    enabled = agent_kind == "personal" or use_knowledge_base
    sources = []
    if enabled:
        yield {"type": "status", "stage": "retrieving", "text": "正在检索资料"}
        try:
            sources = retrieve_for_agent(user_id, agent_id, content)
        except Exception:
            yield {"type": "status", "stage": "retrieval_failed", "text": "资料检索失败，已降级为普通回答"}
        citations = [source.to_citation() for source in sources]
        if citations:
            yield {"type": "status", "stage": "context", "text": f"已命中 {len(citations)} 条资料，正在构造上下文"}
            yield {"type": "sources", "items": citations}
        elif sources == []:
            yield {"type": "status", "stage": "no_match", "text": "未命中已启用的知识库资料"}
    yield {"type": "status", "stage": "generating", "text": "正在生成回答"}
    for delta in stream_answer(system_prompt, history, content, build_retrieval_context(sources)):
        yield {"type": "answer_delta", "content": delta}


def _build_runtime_graph():
    graph = StateGraph(RuntimeState)
    graph.add_node("prepare_input", _prepare_input)
    graph.add_node("model", _run_model)
    graph.add_edge(START, "prepare_input")
    graph.add_edge("prepare_input", "model")
    graph.add_edge("model", END)
    return graph.compile()


def _prepare_input(state: RuntimeState) -> dict[str, list[BaseMessage]]:
    messages: list[BaseMessage] = []
    if state["system_prompt"] and state["system_prompt"].strip():
        messages.append(SystemMessage(content=state["system_prompt"].strip()))
    if state["retrieval_context"]:
        messages.append(SystemMessage(content=state["retrieval_context"]))
    messages.extend(_history_messages(state["history"][-10:]))
    messages.append(HumanMessage(content=state["content"]))
    return {"messages": messages}


def _run_model(state: RuntimeState) -> dict[str, list[BaseMessage]]:
    response = create_chat_model().invoke(state["messages"])
    return {"messages": [response]}


def _history_messages(history: list[ModelMessage]) -> list[BaseMessage]:
    return [HumanMessage(content=item["content"]) if item["role"] == "user" else AIMessage(content=item["content"]) for item in history]


def _message_text(content: str | list[str | dict[str, object]]) -> str:
    if isinstance(content, str):
        return content
    return "".join(item for item in content if isinstance(item, str))
