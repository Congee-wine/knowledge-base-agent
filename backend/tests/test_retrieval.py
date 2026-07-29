import unittest
from unittest.mock import MagicMock, patch

from retrieval.models import RetrievalSource
from repositories.knowledge_retrieval import has_ready_agent_documents
from services.retrieval import _select_context_sources, retrieve_for_agent


class RetrievalTests(unittest.TestCase):
    @patch("repositories.knowledge_retrieval.get_connection")
    def test_ready_document_check_uses_the_knowledge_node_owner(self, get_connection: MagicMock) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"has_documents": True}

        self.assertTrue(has_ready_agent_documents("user-1", "agent-1"))

        query = cursor.execute.call_args.args[0]
        self.assertIn("node.owner_user_id", query)
        self.assertNotIn("version.owner_user_id", query)

    @patch("services.retrieval._record_retrieval_diagnostics")
    @patch("services.retrieval.rerank_query_candidates", return_value=[0.80, 0.20])
    @patch("services.retrieval.knowledge_retrieval.search_agent_chunks_by_keywords", return_value=[])
    @patch("services.retrieval.knowledge_retrieval.search_agent_chunks")
    @patch("services.retrieval.embed_query", return_value=[0.1, 0.2])
    def test_retrieve_for_agent_discards_low_relevance_candidates(self, _: object, search_agent_chunks: object, __: object, ___: object, ____: object) -> None:
        search_agent_chunks.return_value = [
            RetrievalSource("high", "document-1", "mysql.md", "MySQL 是关系型数据库", None, 0, None, 0.75),
            RetrievalSource("low", "document-2", "other.md", "无关内容", None, 0, None, 0.20),
        ]

        sources = retrieve_for_agent("user-1", "agent-1", "数据库基础知识")

        self.assertEqual([source.chunk_id for source in sources], ["high"])

    def test_context_selection_limits_chunks_per_document(self) -> None:
        candidates = [
            RetrievalSource(f"a-{index}", "document-a", "a.md", "内容", None, 0, None, 1.0, rerank_score=0.9 - index / 100)
            for index in range(3)
        ] + [
            RetrievalSource("b-1", "document-b", "b.md", "内容", None, 0, None, 1.0, rerank_score=0.85),
        ]

        selected = _select_context_sources(candidates)

        self.assertEqual([source.chunk_id for source in selected], ["a-0", "a-1", "b-1"])


if __name__ == "__main__":
    unittest.main()
