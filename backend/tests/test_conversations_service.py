from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from database import get_connection
from repositories import conversations as repo
from repositories.agents import BUILTIN_AGENT_ID
from services import conversations as service
from services.errors import DomainError


class ConversationsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid.uuid4()
        self.agent_id = BUILTIN_AGENT_ID
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (self.user_id, f"svc-test-{uuid.uuid4().hex}@example.com", "hashed", datetime.now(timezone.utc)),
                )

    def tearDown(self) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE owner_user_id = %s)",
                    (self.user_id,),
                )
                cursor.execute("DELETE FROM conversations WHERE owner_user_id = %s", (self.user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (self.user_id,))

    def test_echo_flow_does_not_crash_on_none_unpack(self) -> None:
        result = service.send_echo_message(str(self.user_id), self.agent_id, None, "你好")
        self.assertEqual(result.user_message.role, "user")
        self.assertEqual(result.assistant_message.role, "assistant")
        self.assertEqual(result.user_message.content, "你好")
        self.assertEqual(result.assistant_message.content, "已收到你的消息：你好")

    @patch("services.conversations.stream_answer")
    def test_completed_duplicate_request_does_not_call_model(self, mock_stream: object) -> None:
        request_id = uuid.uuid4().hex
        events = list(service.stream_message(
            str(self.user_id), self.agent_id, None, "第一次", request_id
        ))
        completed = [e for e in events if e.get("type") == "message_end"]
        self.assertTrue(len(completed) > 0)

        events2 = list(service.stream_message(
            str(self.user_id), self.agent_id, None, "第一次", request_id
        ))
        types = [e["type"] for e in events2]
        self.assertIn("answer_delta", types)
        self.assertIn("message_end", types)
        self.assertNotIn("error", types)

    @patch("services.conversations.stream_answer", side_effect=Exception("should not be called"))
    def test_generating_duplicate_returns_error(self, mock_stream: object) -> None:
        request_id = uuid.uuid4().hex
        repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "进行中", request_id
        )
        events = list(service.stream_message(
            str(self.user_id), self.agent_id, None, "进行中", request_id
        ))
        error_events = [e for e in events if e.get("type") == "error"]
        self.assertTrue(len(error_events) > 0)
        self.assertEqual(error_events[0]["code"], "REQUEST_IN_PROGRESS")

    def test_second_request_in_same_conversation_is_rejected_while_generating(self) -> None:
        conversation, _, assistant_message, _ = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "第一个问题", uuid.uuid4().hex
        )

        with self.assertRaises(DomainError) as context:
            repo.start_stream_generation(
                str(self.user_id), self.agent_id, str(conversation["id"]), "第二个问题", uuid.uuid4().hex
            )

        self.assertEqual(context.exception.code, "CONVERSATION_GENERATION_IN_PROGRESS")
        repo.interrupt_stream_generation(str(assistant_message["id"]), "")

    def test_conversation_detail_includes_generating_assistant_message(self) -> None:
        conversation, _, assistant_message, _ = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "仍在生成", uuid.uuid4().hex
        )

        detail = service.get_conversation(str(self.user_id), str(conversation["id"]))

        self.assertEqual(detail.messages[-1].id, str(assistant_message["id"]))
        self.assertEqual(detail.messages[-1].generation_status, "generating")
        repo.interrupt_stream_generation(str(assistant_message["id"]), "")

    @patch("services.conversations.stream_answer")
    def test_failed_request_returns_retryable_error(self, mock_stream: object) -> None:
        request_id = uuid.uuid4().hex
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "失败测试", request_id
        )
        _, _, assistant_msg, _ = result
        repo.fail_stream_generation(str(assistant_msg["id"]), "")

        events = list(service.stream_message(
            str(self.user_id), self.agent_id, None, "失败测试", request_id
        ))
        error_events = [e for e in events if e.get("type") == "error"]
        self.assertTrue(len(error_events) > 0)
        self.assertEqual(error_events[0]["code"], "GENERATION_FAILED")
        self.assertTrue(error_events[0]["retryable"])


if __name__ == "__main__":
    unittest.main()
