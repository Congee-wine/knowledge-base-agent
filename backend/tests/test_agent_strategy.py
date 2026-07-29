import unittest
from unittest.mock import patch

from services.agent_strategy import RuntimeStrategy, decide_strategy


class AgentStrategyTests(unittest.TestCase):
    @patch("services.agent_strategy.create_chat_model", side_effect=RuntimeError("provider unavailable"))
    def test_private_document_request_falls_back_to_retrieval_when_available(self, _: object) -> None:
        strategy = decide_strategy("请根据我上传的合同说明付款条件", [], True)

        self.assertEqual(strategy, RuntimeStrategy("knowledge_answer", True, "semantic_search"))

    @patch("services.agent_strategy.create_chat_model", side_effect=RuntimeError("provider unavailable"))
    def test_general_question_falls_back_to_direct_answer(self, _: object) -> None:
        strategy = decide_strategy("请解释什么是向量数据库", [], True)

        self.assertEqual(strategy, RuntimeStrategy("direct_answer", False))

    @patch("services.agent_strategy.create_chat_model")
    def test_private_evidence_without_available_scope_requests_clarification(self, create_chat_model: object) -> None:
        create_chat_model.return_value.invoke.return_value.content = '{"strategy":"knowledge_answer","requiresPrivateEvidence":true,"knowledgeOperation":"semantic_search"}'

        strategy = decide_strategy("根据内部制度回答", [], False)

        self.assertEqual(strategy, RuntimeStrategy("clarify", True))

    @patch("services.agent_strategy.create_chat_model")
    def test_catalog_plan_uses_document_catalog_operation(self, create_chat_model: object) -> None:
        create_chat_model.return_value.invoke.return_value.content = '{"strategy":"knowledge_answer","requiresPrivateEvidence":true,"knowledgeOperation":"document_catalog"}'

        strategy = decide_strategy("知识库有哪些资料？", [], True)

        self.assertEqual(strategy, RuntimeStrategy("knowledge_answer", True, "document_catalog"))


if __name__ == "__main__":
    unittest.main()
