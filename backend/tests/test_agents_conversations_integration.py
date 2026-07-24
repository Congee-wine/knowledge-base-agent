from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from database import get_connection
from main import app
from repositories.agents import BUILTIN_AGENT_ID


PASSWORD = "Integration-Test-Password-2026!"


class AgentsAndConversationsIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_ids: list[str] = []

    def tearDown(self) -> None:
        if not self.user_ids:
            return
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE owner_user_id = ANY(%s))", (self.user_ids,))
                cursor.execute("DELETE FROM conversations WHERE owner_user_id = ANY(%s)", (self.user_ids,))
                cursor.execute("DELETE FROM user_preferences WHERE user_id = ANY(%s)", (self.user_ids,))
                cursor.execute("DELETE FROM agent_preset_questions WHERE agent_id IN (SELECT id FROM agents WHERE owner_user_id = ANY(%s))", (self.user_ids,))
                cursor.execute("DELETE FROM agents WHERE owner_user_id = ANY(%s)", (self.user_ids,))
                cursor.execute("DELETE FROM auth_sessions WHERE user_id = ANY(%s)", (self.user_ids,))
                cursor.execute("DELETE FROM users WHERE id = ANY(%s)", (self.user_ids,))

    def create_headers(self) -> dict[str, str]:
        email = f"agent-test-{uuid.uuid4().hex}@gmail.com"
        registration = self.client.post("/api/auth/register", json={"email": email, "password": PASSWORD, "accepted_terms": True})
        self.assertEqual(registration.status_code, 201)
        self.user_ids.append(registration.json()["id"])
        login = self.client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        self.assertEqual(login.status_code, 200)
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def create_agent(self, headers: dict[str, str], name: str) -> dict[str, object]:
        response = self.client.post(
            "/api/agents",
            headers=headers,
            json={"name": name, "description": "用于集成测试", "presetQuestions": ["测试问题"]},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_entry_defaults_to_builtin_agent(self) -> None:
        headers = self.create_headers()

        response = self.client.get("/api/chat/entry", headers=headers)
        immutable_delete = self.client.delete(f"/api/agents/{BUILTIN_AGENT_ID}", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent"]["id"], BUILTIN_AGENT_ID)
        self.assertEqual(response.json()["agent"]["kind"], "builtin")
        self.assertEqual(immutable_delete.status_code, 409)
        self.assertEqual(immutable_delete.json()["code"], "AGENT_IMMUTABLE")

    def test_default_must_be_cleared_before_soft_delete(self) -> None:
        headers = self.create_headers()
        agent = self.create_agent(headers, "默认测试助手")
        updated = self.client.patch(
            f"/api/agents/{agent['id']}",
            headers=headers,
            json={"welcomeMessage": "更新后的欢迎语", "presetQuestions": ["新的问题"]},
        )

        set_default = self.client.put(f"/api/agents/{agent['id']}/default", headers=headers)
        blocked_delete = self.client.delete(f"/api/agents/{agent['id']}", headers=headers)
        clear_default = self.client.delete("/api/agents/default", headers=headers)
        deleted = self.client.delete(f"/api/agents/{agent['id']}", headers=headers)
        entry = self.client.get("/api/chat/entry", headers=headers)

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["welcomeMessage"], "更新后的欢迎语")
        self.assertEqual(updated.json()["presetQuestions"], ["新的问题"])
        self.assertEqual(set_default.status_code, 200)
        self.assertEqual(blocked_delete.status_code, 409)
        self.assertEqual(blocked_delete.json()["code"], "DEFAULT_AGENT_MUST_BE_CLEARED")
        self.assertEqual(clear_default.status_code, 204)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(entry.json()["agent"]["kind"], "builtin")

    def test_personal_agent_persists_network_entry_visibility(self) -> None:
        headers = self.create_headers()
        created = self.client.post(
            "/api/agents",
            headers=headers,
            json={"name": "联网测试助手", "allowNetworkAccess": True},
        )
        updated = self.client.patch(
            f"/api/agents/{created.json()['id']}",
            headers=headers,
            json={"allowNetworkAccess": False},
        )

        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.json()["allowNetworkAccess"])
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["allowNetworkAccess"])

    def test_agents_and_conversations_are_isolated_by_user(self) -> None:
        owner_headers = self.create_headers()
        other_headers = self.create_headers()
        owner_agent = self.create_agent(owner_headers, "仅属于第一个用户")
        owner_conversation = self.client.post(
            "/api/conversations",
            headers=owner_headers,
            json={"agentId": owner_agent["id"], "title": "我的会话"},
        )

        other_agent = self.client.get(f"/api/agents/{owner_agent['id']}", headers=other_headers)
        other_conversation = self.client.get(f"/api/conversations/{owner_conversation.json()['id']}", headers=other_headers)
        other_create = self.client.post("/api/conversations", headers=other_headers, json={"agentId": owner_agent["id"]})
        other_message = self.client.post(
            f"/api/conversations/{owner_conversation.json()['id']}/messages",
            headers=other_headers,
            json={"content": "越权消息"},
        )

        self.assertEqual(owner_conversation.status_code, 201)
        self.assertEqual(other_agent.status_code, 404)
        self.assertEqual(other_conversation.status_code, 404)
        self.assertEqual(other_create.status_code, 404)
        self.assertEqual(other_message.status_code, 404)

    def test_conversation_list_only_returns_current_agent_records(self) -> None:
        headers = self.create_headers()
        first_agent = self.create_agent(headers, "第一个助手")
        second_agent = self.create_agent(headers, "第二个助手")
        first_conversation = self.client.post("/api/conversations", headers=headers, json={"agentId": first_agent["id"], "title": "第一条"})
        self.client.post("/api/conversations", headers=headers, json={"agentId": second_agent["id"], "title": "第二条"})

        response = self.client.get(f"/api/conversations?agentId={first_agent['id']}", headers=headers)

        self.assertEqual(first_conversation.status_code, 201)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["items"]], [first_conversation.json()["id"]])

    def test_only_one_empty_conversation_is_created_per_agent(self) -> None:
        headers = self.create_headers()

        first = self.client.post("/api/conversations", headers=headers, json={"agentId": BUILTIN_AGENT_ID})
        duplicate = self.client.post("/api/conversations", headers=headers, json={"agentId": BUILTIN_AGENT_ID})
        self.client.post(f"/api/conversations/{first.json()['id']}/messages", headers=headers, json={"content": "开始对话"})
        next_conversation = self.client.post("/api/conversations", headers=headers, json={"agentId": BUILTIN_AGENT_ID})

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["id"], first.json()["id"])
        self.assertEqual(next_conversation.status_code, 201)
        self.assertNotEqual(next_conversation.json()["id"], first.json()["id"])

    def test_first_message_creates_conversation_without_a_draft_record(self) -> None:
        headers = self.create_headers()

        before = self.client.get(f"/api/conversations?agentId={BUILTIN_AGENT_ID}", headers=headers)
        response = self.client.post(
            "/api/conversations/messages",
            headers=headers,
            json={"agentId": BUILTIN_AGENT_ID, "content": "延迟创建的第一条消息"},
        )
        detail = self.client.get(f"/api/conversations/{response.json()['conversation']['id']}", headers=headers)

        self.assertEqual(before.status_code, 200)
        self.assertEqual(before.json()["items"], [])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["conversation"]["title"], "延迟创建的第一条消息")
        self.assertEqual([message["role"] for message in detail.json()["messages"]], ["user", "assistant"])

    def test_delayed_send_rejects_conversation_from_another_agent(self) -> None:
        headers = self.create_headers()
        other_agent = self.create_agent(headers, "另一智能体")
        started = self.client.post(
            "/api/conversations/messages",
            headers=headers,
            json={"agentId": BUILTIN_AGENT_ID, "content": "内置智能体消息"},
        )
        rejected = self.client.post(
            "/api/conversations/messages",
            headers=headers,
            json={
                "agentId": other_agent["id"],
                "conversationId": started.json()["conversation"]["id"],
                "content": "不应写入",
            },
        )
        detail = self.client.get(f"/api/conversations/{started.json()['conversation']['id']}", headers=headers)

        self.assertEqual(started.status_code, 201)
        self.assertEqual(rejected.status_code, 404)
        self.assertEqual([message["content"] for message in detail.json()["messages"]], [
            "内置智能体消息", "已收到你的消息：内置智能体消息",
        ])

    def test_echo_message_persists_both_roles_and_updates_conversation(self) -> None:
        headers = self.create_headers()
        conversation = self.client.post(
            "/api/conversations",
            headers=headers,
            json={"agentId": BUILTIN_AGENT_ID},
        ).json()

        response = self.client.post(
            f"/api/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"content": "  请介绍报价政策  "},
        )
        detail = self.client.get(f"/api/conversations/{conversation['id']}", headers=headers)
        blank_message = self.client.post(
            f"/api/conversations/{conversation['id']}/messages",
            headers=headers,
            json={"content": "   "},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["conversation"]["title"], "请介绍报价政策")
        self.assertEqual(response.json()["userMessage"]["role"], "user")
        self.assertEqual(response.json()["userMessage"]["content"], "请介绍报价政策")
        self.assertEqual(response.json()["assistantMessage"]["role"], "assistant")
        self.assertEqual(response.json()["assistantMessage"]["content"], "已收到你的消息：请介绍报价政策")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual([message["role"] for message in detail.json()["messages"]], ["user", "assistant"])
        self.assertEqual(blank_message.status_code, 422)


if __name__ == "__main__":
    unittest.main()
