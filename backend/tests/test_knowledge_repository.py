from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from repositories import knowledge


class KnowledgeRepositoryTests(unittest.TestCase):
    @patch("repositories.knowledge.get_connection")
    def test_delete_node_tree_removes_embedding_jobs_before_document_versions(self, get_connection: MagicMock) -> None:
        connection, cursor = MagicMock(), MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        cursor.fetchone.return_value = {"exists": 1}
        cursor.fetchall.return_value = [{"storage_key": "knowledge-files/user-1/file.txt"}]

        storage_keys = knowledge.delete_node_tree("node-1", "user-1")

        statements = [invocation.args[0] for invocation in cursor.execute.call_args_list]
        embedding_delete = next(index for index, statement in enumerate(statements) if "DELETE FROM embedding_jobs" in statement)
        version_delete = next(index for index, statement in enumerate(statements) if "DELETE FROM document_versions" in statement)
        self.assertLess(embedding_delete, version_delete)
        self.assertEqual(storage_keys, ["knowledge-files/user-1/file.txt"])


if __name__ == "__main__":
    unittest.main()
