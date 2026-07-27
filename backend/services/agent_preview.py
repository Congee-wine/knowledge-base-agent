from __future__ import annotations

from collections.abc import Iterator

from integrations.deepseek import DeepSeekError
from schemas.streaming import PreviewStreamRequest
from services.agent_runtime import ModelMessage, stream_answer
from services.agents import get_agent


def stream_preview(user_id: str, agent_id: str, data: PreviewStreamRequest) -> Iterator[dict[str, object]]:
    agent = get_agent(user_id, agent_id)
    if agent.kind != "personal":
        raise ValueError("Only personal agents can be previewed")
    history: list[ModelMessage] = [{"role": item.role, "content": item.content} for item in data.history]

    def events() -> Iterator[dict[str, object]]:
        yield {"type": "message_start"}
        yield {"type": "status", "stage": "generating", "text": "正在生成回答"}
        try:
            for delta in stream_answer(data.draft_agent.system_prompt, history, data.content):
                yield {"type": "answer_delta", "content": delta}
            yield {"type": "message_end", "generationStatus": "complete"}
        except DeepSeekError:
            yield {"type": "error", "code": "MODEL_UNAVAILABLE", "message": "模型服务暂时不可用", "retryable": True}
        except Exception:
            yield {"type": "error", "code": "PREVIEW_RUNTIME_FAILED", "message": "预览运行失败，请稍后重试", "retryable": True}

    return events()
