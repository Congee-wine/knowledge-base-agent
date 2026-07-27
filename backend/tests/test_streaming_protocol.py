from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from routers.agents import _preview_sse
from routers.conversations import _sse
from services import agent_preview


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


if __name__ == "__main__":
    unittest.main()
