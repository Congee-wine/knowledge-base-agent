from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from routers.agents import _preview_sse
from routers.conversations import _sse, stream_message as stream_message_route
from services import agent_preview
from services import conversations as conversation_service
from services.errors import DomainError


def _frame_data(frame: str) -> dict[str, object]:
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    return json.loads(data_line.removeprefix("data: "))


class StreamingProtocolTests(unittest.TestCase):
    def test_preview_sse_uses_mode_without_persisted_identifiers(self) -> None:
        events = [
            {"type": "message_start"},
            {"type": "message_end", "generationStatus": "complete"},
        ]

        payloads = [_frame_data(frame) for frame in _preview_sse(events, "request-1")]

        self.assertEqual([payload["mode"] for payload in payloads], ["preview", "preview"])
        self.assertEqual([payload["sequence"] for payload in payloads], [1, 2])
        self.assertNotIn("conversationId", payloads[0])
        self.assertNotIn("messageId", payloads[1])

    def test_conversation_sse_uses_mode_and_persisted_identifiers(self) -> None:
        events = [{
            "type": "message_start",
            "conversationId": "conversation-1",
            "userMessageId": "user-1",
            "assistantMessageId": "assistant-1",
        }]

        payload = _frame_data(next(_sse(events, "request-1", "conversation")))

        self.assertEqual(payload["mode"], "conversation")
        self.assertEqual(payload["conversationId"], "conversation-1")
        self.assertEqual(payload["assistantMessageId"], "assistant-1")

    @patch("services.agent_preview.get_agent", return_value=SimpleNamespace(kind="builtin"))
    def test_preview_permission_is_validated_before_iteration(self, _: object) -> None:
        request = SimpleNamespace(history=[], draft_agent=SimpleNamespace(system_prompt=None), content="hello")

        with self.assertRaisesRegex(ValueError, "Only personal agents"):
            agent_preview.stream_preview("user-1", "agent-1", request)

    @patch("services.conversations.conversation_repository.complete_stream_generation")
    @patch("services.conversations.stream_with_retrieval", return_value=iter([{"type": "answer_delta", "content": "answer"}]))
    @patch("services.conversations.conversation_repository.list_valid_history")
    @patch("services.conversations.conversation_repository.start_stream_generation")
    @patch("services.conversations._ensure_active_agent", return_value=SimpleNamespace(kind="personal", system_prompt="prompt", name="测试智能体", description="测试职责"))
    def test_conversation_runtime_uses_only_valid_history(
        self,
        _: object,
        start_generation: object,
        list_history: object,
        stream_with_retrieval: object,
        complete_generation: object,
    ) -> None:
        conversation = {"id": "conversation-1"}
        user_message = {"id": "user-1", "message_order": 7}
        assistant_message = {"id": "assistant-1", "generation_status": "generating"}
        start_generation.return_value = conversation, user_message, assistant_message, True
        list_history.return_value = [{"role": "user", "content": "previous question"}]

        events = list(conversation_service.stream_message("user-1", "agent-1", "conversation-1", "new question", "request-1"))

        list_history.assert_called_once_with("conversation-1", 7, 10)
        stream_with_retrieval.assert_called_once_with(
            "user-1", "agent-1", "personal", "prompt", [{"role": "user", "content": "previous question"}], "new question", False,
            "测试智能体", "测试职责",
        )
        complete_generation.assert_called_once_with("assistant-1", "answer", [])
        self.assertEqual(events[-1]["type"], "message_end")

    def test_resume_request_is_rejected_before_stream_creation(self) -> None:
        request = SimpleNamespace(after_sequence=1, content="hello", request_id="request-1")

        with self.assertRaises(DomainError) as captured:
            stream_message_route(request, "agent-1", None, SimpleNamespace(id="user-1"))

        self.assertEqual(captured.exception.code, "STREAM_RESUME_UNAVAILABLE")

    @patch("services.conversations.conversation_repository.interrupt_stream_generation_for_user")
    def test_interrupt_persists_the_partial_answer(self, interrupt_generation: object) -> None:
        interrupt_generation.return_value = {
            "id": "assistant-1",
            "role": "assistant",
            "content": "partial answer",
            "generation_status": "interrupted",
            "created_at": datetime.now(timezone.utc),
        }

        message = conversation_service.interrupt_stream_message("user-1", "assistant-1", "partial answer")

        interrupt_generation.assert_called_once_with("user-1", "assistant-1", "partial answer")
        self.assertEqual(message.generation_status, "interrupted")
        self.assertEqual(message.content, "partial answer")


if __name__ == "__main__":
    unittest.main()
