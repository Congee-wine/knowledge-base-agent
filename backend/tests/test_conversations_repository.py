from __future__ import annotations

import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Lock
from unittest.mock import patch

from database import get_connection
from repositories import conversations as repo
from repositories.agents import BUILTIN_AGENT_ID


class ConversationsRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid.uuid4()
        self.agent_id = BUILTIN_AGENT_ID
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (self.user_id, f"repo-test-{uuid.uuid4().hex}@example.com", "hashed", datetime.now(timezone.utc)),
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

    def test_append_echo_messages_returns_complete_triple(self) -> None:
        conversation, _ = repo.create_conversation(self.user_id, self.agent_id, None)
        result = repo.append_echo_messages(str(self.user_id), str(conversation["id"]), "你好")
        self.assertIsNotNone(result)
        conv, user_msg, assistant_msg = result
        self.assertEqual(user_msg["role"], "user")
        self.assertEqual(user_msg["content"], "你好")
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg["content"], "已收到你的消息：你好")
        self.assertEqual(assistant_msg["generation_status"], "complete")
        self.assertEqual(str(assistant_msg["reply_to_message_id"]), str(user_msg["id"]))
        self.assertEqual((user_msg["message_order"], assistant_msg["message_order"]), (1, 2))

    def test_start_stream_generation_creates_messages_with_reply_relation(self) -> None:
        request_id = uuid.uuid4().hex
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "流式问题", request_id
        )
        self.assertIsNotNone(result)
        conv, user_msg, assistant_msg, created = result
        self.assertTrue(created)
        self.assertEqual(user_msg["role"], "user")
        self.assertEqual(user_msg["content"], "流式问题")
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg["generation_status"], "generating")
        self.assertEqual(assistant_msg["client_request_id"], request_id)
        self.assertEqual(str(assistant_msg["reply_to_message_id"]), str(user_msg["id"]))
        self.assertEqual((user_msg["message_order"], assistant_msg["message_order"]), (1, 2))

    def test_complete_stream_generation_updates_content_and_status(self) -> None:
        request_id = uuid.uuid4().hex
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "测试完成", request_id
        )
        conversation, _, assistant_msg, _ = result
        previous_updated_at = conversation["updated_at"]
        updated = repo.complete_stream_generation(str(assistant_msg["id"]), "最终回答")
        self.assertEqual(updated["content"], "最终回答")
        self.assertEqual(updated["generation_status"], "complete")
        refreshed = repo.get_conversation(str(self.user_id), str(conversation["id"]))
        self.assertIsNotNone(refreshed)
        self.assertGreater(refreshed["updated_at"], previous_updated_at)

    def test_interrupt_stream_generation_sets_interrupted(self) -> None:
        request_id = uuid.uuid4().hex
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "测试中断", request_id
        )
        _, _, assistant_msg, _ = result
        updated = repo.interrupt_stream_generation(str(assistant_msg["id"]), "部分回答")
        self.assertEqual(updated["content"], "部分回答")
        self.assertEqual(updated["generation_status"], "interrupted")

    def test_fail_stream_generation_sets_failed(self) -> None:
        request_id = uuid.uuid4().hex
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "测试失败", request_id
        )
        _, _, assistant_msg, _ = result
        updated = repo.fail_stream_generation(str(assistant_msg["id"]), "")
        self.assertEqual(updated["generation_status"], "failed")

    def test_idempotent_request_returns_same_messages(self) -> None:
        request_id = uuid.uuid4().hex
        repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "幂等测试", request_id
        )
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "幂等测试", request_id
        )
        self.assertIsNotNone(result)
        conv, user_msg, assistant_msg, created = result
        self.assertFalse(created)
        self.assertEqual(user_msg["content"], "幂等测试")
        self.assertEqual(str(assistant_msg["reply_to_message_id"]), str(user_msg["id"]))

    def test_idempotent_request_only_creates_one_pair(self) -> None:
        request_id = uuid.uuid4().hex
        repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "唯一性测试", request_id
        )
        repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "唯一性测试", request_id
        )
        convs = repo.list_conversations(str(self.user_id), self.agent_id, 100)
        self.assertEqual(len(convs), 1)
        messages = repo.list_messages(str(convs[0]["id"]))
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        self.assertEqual(len(user_messages), 1)
        self.assertEqual(len(assistant_messages), 1)

    def test_concurrent_idempotent_request_returns_one_message_pair(self) -> None:
        request_id = uuid.uuid4().hex
        barrier = Barrier(2)
        lock = Lock()
        lookup_count = 0
        original_lookup = repo._find_existing_stream_request

        def synchronized_lookup(cursor: object, current_request_id: str, user_id: str):
            nonlocal lookup_count
            with lock:
                lookup_count += 1
                wait_for_peer = lookup_count <= 2
            if wait_for_peer:
                barrier.wait(timeout=10)
            return original_lookup(cursor, current_request_id, user_id)

        def start_request() -> tuple[object, object, object, bool] | None:
            return repo.start_stream_generation(
                str(self.user_id), self.agent_id, None, "并发幂等测试", request_id
            )

        with patch.object(repo, "_find_existing_stream_request", side_effect=synchronized_lookup):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = [future.result(timeout=20) for future in (executor.submit(start_request), executor.submit(start_request))]

        self.assertTrue(all(result is not None for result in results))
        assert results[0] is not None and results[1] is not None
        self.assertEqual(sum(result[3] for result in results), 1)
        self.assertEqual(str(results[0][1]["id"]), str(results[1][1]["id"]))
        self.assertEqual(str(results[0][2]["id"]), str(results[1][2]["id"]))
        conversations = repo.list_conversations(str(self.user_id), self.agent_id, 10)
        self.assertEqual(len(conversations), 1)

    def test_stream_start_activates_existing_draft_conversation(self) -> None:
        draft, created = repo.create_conversation(self.user_id, self.agent_id, None)
        self.assertTrue(created)
        self.assertTrue(draft["is_draft"])

        conversation, _, _, created = repo.start_stream_generation(
            str(self.user_id), self.agent_id, str(draft["id"]), "草稿会话首条消息", uuid.uuid4().hex
        )

        self.assertTrue(created)
        self.assertFalse(conversation["is_draft"])
        self.assertEqual(conversation["title"], "草稿会话首条消息")
        self.assertGreater(conversation["updated_at"], draft["updated_at"])

    def test_complete_nonexistent_message_raises(self) -> None:
        from services.errors import DomainError
        fake_id = str(uuid.uuid4())
        with self.assertRaises(DomainError):
            repo.complete_stream_generation(fake_id, "不存在")

    def test_stream_status_update_rejects_user_message(self) -> None:
        result = repo.start_stream_generation(
            str(self.user_id), self.agent_id, None, "不应更新 user 消息", uuid.uuid4().hex
        )
        _, user_message, _, _ = result

        from services.errors import DomainError

        with self.assertRaises(DomainError):
            repo.complete_stream_generation(str(user_message["id"]), "错误更新")

    def test_cross_conversation_reply_is_rejected(self) -> None:
        first, _ = repo.create_conversation(self.user_id, self.agent_id, "会话一")
        second, _ = repo.create_conversation(self.user_id, self.agent_id, "会话二")
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, generation_status, message_order, created_at)
                    VALUES (%s, %s, 'user', 'question', 'complete', 1, %s) RETURNING *""",
                    (uuid.uuid4(), str(first["id"]), datetime.now(timezone.utc)),
                )
                user_message = cursor.fetchone()
                cursor.execute("SAVEPOINT cross_conversation_reply")
                with self.assertRaises(Exception):
                    cursor.execute(
                        """INSERT INTO messages (id, conversation_id, role, content, generation_status, reply_to_message_id, message_order, created_at)
                        VALUES (%s, %s, 'assistant', 'answer', 'complete', %s, 1, %s)""",
                        (uuid.uuid4(), str(second["id"]), user_message["id"], datetime.now(timezone.utc)),
                    )
                cursor.execute("ROLLBACK TO SAVEPOINT cross_conversation_reply")

    def test_legacy_stream_request_without_reply_relation_is_rejected(self) -> None:
        conversation, _ = repo.create_conversation(self.user_id, self.agent_id, "旧请求")
        request_id = uuid.uuid4().hex
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, generation_status, client_request_id, message_order, created_at)
                    VALUES (%s, %s, 'assistant', '', 'failed', %s, 1, %s)""",
                    (uuid.uuid4(), str(conversation["id"]), request_id, datetime.now(timezone.utc)),
                )

        from services.errors import DomainError

        with self.assertRaisesRegex(DomainError, "重新发送"):
            repo.start_stream_generation(str(self.user_id), self.agent_id, str(conversation["id"]), "重试", request_id)

    def test_reply_to_requires_assistant_role(self) -> None:
        """User messages must not have reply_to_message_id set."""
        conversation, _ = repo.create_conversation(self.user_id, self.agent_id, None)
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, generation_status, message_order, created_at)
                    VALUES (%s, %s, 'user', 'x', 'complete', 1, %s) RETURNING *""",
                    (uuid.uuid4(), str(conversation["id"]), datetime.now(timezone.utc)),
                )
                user_msg = cursor.fetchone()
                with self.assertRaises(Exception):
                    cursor.execute(
                        """INSERT INTO messages (id, conversation_id, role, content, generation_status, reply_to_message_id, message_order, created_at)
                        VALUES (%s, %s, 'user', 'y', 'complete', %s, 2, %s)""",
                        (uuid.uuid4(), str(conversation["id"]), user_msg["id"], datetime.now(timezone.utc)),
                    )
                connection.rollback()

    def test_list_messages_uses_message_order_when_timestamps_are_reversed(self) -> None:
        conversation, _ = repo.create_conversation(self.user_id, self.agent_id, "顺序")
        user_message_id = uuid.uuid4()
        with get_connection() as connection:
            with connection.cursor() as cursor:
                now = datetime.now(timezone.utc)
                cursor.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, generation_status, message_order, created_at)
                    VALUES (%s, %s, 'user', '问题', 'complete', 1, %s)""",
                    (user_message_id, str(conversation["id"]), now + timedelta(seconds=1)),
                )
                cursor.execute(
                    """INSERT INTO messages (id, conversation_id, role, content, generation_status, reply_to_message_id, message_order, created_at)
                    VALUES (%s, %s, 'assistant', '回答', 'complete', %s, 2, %s)""",
                    (uuid.uuid4(), str(conversation["id"]), user_message_id, now),
                )

        messages = repo.list_messages(str(conversation["id"]))
        self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
        self.assertEqual([message["message_order"] for message in messages], [1, 2])


if __name__ == "__main__":
    unittest.main()
