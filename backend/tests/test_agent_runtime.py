import unittest
from unittest.mock import patch

from services.agent_runtime import stream_with_retrieval
from retrieval.models import RetrievalSource
from services.agent_strategy import RuntimeStrategy


class AgentRuntimeTests(unittest.TestCase):
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

    @patch("services.agent_runtime.stream_answer", return_value=iter(["通用回答"]))
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.decide_strategy", return_value=RuntimeStrategy("direct_answer", False))
    def test_direct_strategy_does_not_query_knowledge_base(self, _: object, execute_operation: object, __: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "解释向量数据库", False))

        execute_operation.assert_not_called()
        self.assertEqual([event["type"] for event in events], ["status", "status", "answer_delta"])
        self.assertEqual(events[-1]["content"], "通用回答")

    @patch("services.agent_runtime.stream_answer", return_value=iter(["请上传对应制度或说明具体文件。 "]))
    @patch("services.agent_runtime.execute_knowledge_operation", return_value=[])
    @patch("services.agent_runtime.decide_strategy", return_value=RuntimeStrategy("knowledge_answer", True))
    def test_missing_required_private_evidence_becomes_clarification(self, _: object, __: object, ___: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "根据制度回答", False))

        stages = [event.get("stage") for event in events if event["type"] == "status"]
        self.assertIn("no_match", stages)
        self.assertIn("clarifying", stages)
        self.assertEqual(events[-1]["type"], "answer_delta")

    @patch("services.agent_runtime.stream_answer")
    @patch("services.agent_runtime.execute_knowledge_operation")
    @patch("services.agent_runtime.decide_strategy", return_value=RuntimeStrategy("knowledge_answer", True, "document_catalog"))
    def test_catalog_operation_lists_tool_documents_without_model(self, _: object, execute_operation: object, stream_answer: object) -> None:
        execute_operation.return_value = [
            RetrievalSource("chunk-1", "document-1", "资料一.md", "内容", None, 0, None, 1.0),
            RetrievalSource("chunk-2", "document-2", "资料二.pdf", "内容", None, 0, None, 1.0),
        ]

        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "知识库有哪些文件？", False))

        execute_operation.assert_called_once_with("document_catalog", "user-1", "agent-1", "知识库有哪些文件？")
        stream_answer.assert_not_called()
        self.assertIn("资料一.md", str(events[-1]["content"]))
        self.assertIn("资料二.pdf", str(events[-1]["content"]))


if __name__ == "__main__":
    unittest.main()
