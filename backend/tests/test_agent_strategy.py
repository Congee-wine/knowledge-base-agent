import unittest

from services.agent_strategy import RuntimeStrategy, decide_strategy


class AgentStrategyTests(unittest.TestCase):
    def test_general_question_uses_semantic_search_when_knowledge_is_enabled(self) -> None:
        strategy = decide_strategy("请解释什么是向量数据库", [], True)

        self.assertEqual(strategy, RuntimeStrategy("knowledge_answer", True, "semantic_search"))

    def test_catalog_question_uses_document_catalog(self) -> None:
        strategy = decide_strategy("知识库有哪些资料？", [], True)

        self.assertEqual(strategy, RuntimeStrategy("knowledge_answer", True, "document_catalog"))

    def test_general_mode_does_not_select_a_knowledge_operation(self) -> None:
        strategy = decide_strategy("请解释什么是向量数据库", [], False)

        self.assertEqual(strategy, RuntimeStrategy("direct_answer", False))


if __name__ == "__main__":
    unittest.main()
