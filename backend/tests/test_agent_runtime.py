import unittest
from unittest.mock import patch

from services.agent_runtime import stream_with_retrieval
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
    @patch("services.agent_runtime.retrieve_for_agent")
    @patch("services.agent_runtime.decide_strategy", return_value=RuntimeStrategy("direct_answer", False))
    def test_direct_strategy_does_not_query_knowledge_base(self, _: object, retrieve_for_agent: object, __: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "解释向量数据库", False))

        retrieve_for_agent.assert_not_called()
        self.assertEqual([event["type"] for event in events], ["status", "status", "answer_delta"])
        self.assertEqual(events[-1]["content"], "通用回答")

    @patch("services.agent_runtime.stream_answer", return_value=iter(["请上传对应制度或说明具体文件。 "]))
    @patch("services.agent_runtime.retrieve_for_agent", return_value=[])
    @patch("services.agent_runtime.decide_strategy", return_value=RuntimeStrategy("knowledge_answer", True))
    def test_missing_required_private_evidence_becomes_clarification(self, _: object, __: object, ___: object) -> None:
        events = list(stream_with_retrieval("user-1", "agent-1", "personal", None, [], "根据制度回答", False))

        stages = [event.get("stage") for event in events if event["type"] == "status"]
        self.assertIn("no_match", stages)
        self.assertIn("clarifying", stages)
        self.assertEqual(events[-1]["type"], "answer_delta")


if __name__ == "__main__":
    unittest.main()
