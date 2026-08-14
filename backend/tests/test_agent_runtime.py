import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessageChunk

from services.agent_runtime import stream_answer, stream_with_retrieval
from retrieval.models import RetrievalSource
from services.agent_strategy import RuntimeStrategy


class AgentRuntimeTests(unittest.TestCase):
    @patch("services.agent_runtime.create_chat_model")
    def test_stream_answer_yields_each_model_chunk(self, create_chat_model: MagicMock) -> None:
        model = MagicMock()
        model.stream.return_value = [AIMessageChunk(content="第一段"), AIMessageChunk(content="第二段")]
        create_chat_model.return_value = model

        chunks = list(stream_answer(None, [], "请分段回答"))

        self.assertEqual(chunks, ["第一段", "第二段"])
        model.stream.assert_called_once()
        model.invoke.assert_not_called()

    @patch("services.agent_runtime.decide_strategy")
    @patch("services.agent_runtime.stream_answer")
    def test_model_question_uses_fixed_profile_without_calling_model(self, stream_answer: object, decide_strategy: object) -> None:
        events = list(stream_with_retrieval(
            "user-1", "agent-1", "personal", None, [], "你背后调用什么模型？", False, "AI 管家", None,
        ))

        stream_answer.assert_not_called()
        decide_strategy.assert_not_called()
        self.assertEqual([event["type"] for event in events], ["status", "answer_delta"])
        self.assertNotIn("模型", str(events[-1]["content"]))

    @patch("services.agent_runtime.has_knowledge_scope", return_value=False)
    @patch("services.agent_runtime.has_ready_knowledge")
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.stream_answer", return_value=iter(["通用回答"]))
    def test_unbound_personal_agent_uses_model_with_explicit_status(
        self, stream_answer: object, execute_operation: object, has_ready_knowledge: object, _: object,
    ) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "解释 RAG", False))

        has_ready_knowledge.assert_not_called()
        execute_operation.assert_not_called()
        stream_answer.assert_called_once()
        statuses = [event["text"] for event in events if event["type"] == "status"]
        self.assertTrue(any("未绑定知识库" in text for text in statuses))
        self.assertEqual([event["content"] for event in events if event["type"] == "answer_delta"], ["通用回答"])

    @patch("services.agent_runtime.has_ready_knowledge")
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.stream_answer", return_value=iter(["通用回答"]))
    def test_builtin_agent_with_knowledge_disabled_uses_model_without_retrieval(
        self, stream_answer: object, execute_operation: object, has_ready_knowledge: object,
    ) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "builtin", None, [], "解释 RAG", False))

        has_ready_knowledge.assert_not_called()
        execute_operation.assert_not_called()
        stream_answer.assert_called_once()
        statuses = [event["text"] for event in events if event["type"] == "status"]
        self.assertFalse(any("未绑定知识库" in text for text in statuses))

    @patch("services.agent_runtime.has_knowledge_scope", return_value=True)
    @patch("services.agent_runtime.stream_answer", return_value=iter(["资料", "回答"]))
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.has_ready_knowledge", return_value=True)
    def test_general_question_always_queries_ready_knowledge_base(self, _: object, execute_operation: object, __: object, ___: object) -> None:
        execute_operation.return_value = [RetrievalSource("chunk-1", "document-1", "mysql.md", "数据库基础知识", None, 0, None, 0.8)]
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "解释向量数据库", False))

        execute_operation.assert_called_once_with("semantic_search", "user-1", "agent-1", "解释向量数据库")
        answer_chunks = [event["content"] for event in events if event["type"] == "answer_delta"]
        self.assertEqual(answer_chunks, ["资料", "回答"])

    @patch("services.agent_runtime.has_knowledge_scope", return_value=True)
    @patch("services.agent_runtime.stream_answer", return_value=iter(["资料概览"] ))
    @patch("services.agent_runtime.execute_knowledge_operation", return_value=[])
    @patch("services.agent_runtime.has_ready_knowledge", return_value=True)
    def test_no_matching_knowledge_does_not_fall_back_to_model_answer(self, _: object, __: object, stream_answer: object, ___: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "根据制度回答", False))

        stages = [event.get("stage") for event in events if event["type"] == "status"]
        self.assertIn("no_match", stages)
        stream_answer.assert_not_called()
        self.assertEqual(events[-1]["type"], "answer_delta")
        self.assertIn("未找到", str(events[-1]["content"]))

    @patch("services.agent_runtime.has_knowledge_scope", return_value=True)
    @patch("services.agent_runtime.stream_answer")
    @patch("services.agent_runtime.execute_knowledge_operation", side_effect=TimeoutError("worker timeout"))
    @patch("services.agent_runtime.has_ready_knowledge", return_value=True)
    def test_retrieval_failure_is_not_reported_as_no_match(self, _: object, __: object, stream_answer: object, ___: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "database basics", False))

        stages = [event.get("stage") for event in events if event["type"] == "status"]
        self.assertIn("retrieval_failed", stages)
        self.assertNotIn("no_match", stages)
        stream_answer.assert_not_called()
        self.assertIn("\u77e5\u8bc6\u5e93", str(events[-1]["content"]))

    @patch("services.agent_runtime.has_knowledge_scope", return_value=True)
    @patch("services.agent_runtime.stream_answer", return_value=iter(["资料概览"]))
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.has_ready_knowledge", return_value=False)
    def test_missing_ready_documents_reports_knowledge_base_unavailable(self, _: object, execute_operation: object, stream_answer: object, __: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "数据库基础知识", False))

        execute_operation.assert_not_called()
        stream_answer.assert_not_called()
        self.assertIn("no_documents", [event.get("stage") for event in events if event["type"] == "status"])
        self.assertIn("没有已完成索引", str(events[-1]["content"]))

    @patch("services.agent_runtime.has_knowledge_scope", return_value=True)
    @patch("services.agent_runtime.stream_answer", return_value=iter(["资料概览"]))
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.has_ready_knowledge", return_value=True)
    def test_overview_operation_uses_documents_to_generate_a_model_overview(self, _: object, execute_operation: object, stream_answer: object, __: object) -> None:
        execute_operation.return_value = [
            RetrievalSource("chunk-1", "document-1", "资料一.md", "内容", None, 0, None, 1.0),
            RetrievalSource("chunk-2", "document-2", "资料二.pdf", "内容", None, 0, None, 1.0),
        ]

        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "知识库有哪些文件？", False))

        execute_operation.assert_called_once_with("knowledge_overview", "user-1", "agent-1", "知识库有哪些文件？")
        stream_answer.assert_called_once()
        self.assertIn("资料概览", [event["content"] for event in events if event["type"] == "answer_delta"])
        context = stream_answer.call_args.args[3]
        self.assertIn("资料一.md", context)
        self.assertIn("资料二.pdf", context)


if __name__ == "__main__":
    unittest.main()
