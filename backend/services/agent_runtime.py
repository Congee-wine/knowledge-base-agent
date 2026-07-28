from __future__ import annotations

from collections.abc import Iterator
from typing import TypedDict

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from integrations.deepseek import DeepSeekError, create_chat_model


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
