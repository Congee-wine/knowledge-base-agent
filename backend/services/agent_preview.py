from __future__ import annotations

from collections.abc import Iterator

from schemas.streaming import PreviewStreamRequest
from services.agent_runtime import ModelMessage, stream_with_retrieval
from services.agents import get_agent


def stream_preview(user_id: str, agent_id: str, data: PreviewStreamRequest) -> Iterator[dict[str, object]]:
    agent = get_agent(user_id, agent_id)
    if agent.kind != "personal":
        raise ValueError("Only personal agents can be previewed")
    history: list[ModelMessage] = [{"role": item.role, "content": item.content} for item in data.history]

    def events() -> Iterator[dict[str, object]]:
        yield {"type": "message_start"}
        try:
            yield from stream_with_retrieval(
                user_id, agent_id, agent.kind, data.draft_agent.system_prompt, history, data.content, True,
            )
            yield {"type": "message_end", "generationStatus": "complete"}
        except Exception:
            yield {"type": "error", "code": "MODEL_UNAVAILABLE", "message": "模型服务暂时不可用", "retryable": True}

    return events()
