from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from services import knowledge
from services.errors import DomainError


def _node(node_id: str, parent_id: str | None, node_type: str, name: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        "id": node_id,
        "parent_id": parent_id,
        "node_type": node_type,
        "name": name,
        "processing_status": None,
        "created_at": now,
        "updated_at": now,
    }


class KnowledgeServiceTests(unittest.TestCase):
    @patch("services.knowledge.knowledge_repository.list_nodes")
    def test_tree_keeps_children_under_their_owned_folder(self, list_nodes: object) -> None:
        folder_id, file_id = str(uuid4()), str(uuid4())
        list_nodes.return_value = [_node(folder_id, None, "folder", "资料"), _node(file_id, folder_id, "file", "说明.txt")]

        tree = knowledge.list_knowledge_tree("user-1")

        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0].id, folder_id)
        self.assertEqual([child.id for child in tree[0].children], [file_id])

    @patch("services.knowledge.knowledge_repository.find_owned_node", return_value={"node_type": "file"})
    def test_file_cannot_be_a_parent_folder(self, _: object) -> None:
        with self.assertRaises(DomainError) as captured:
            knowledge.create_folder("user-1", "file-1", "子目录")

        self.assertEqual(captured.exception.code, "INVALID_PARENT_NODE")

    @patch("services.knowledge.knowledge_repository.sibling_name_exists", return_value=True)
    def test_duplicate_sibling_name_is_rejected(self, _: object) -> None:
        with self.assertRaises(DomainError) as captured:
            knowledge.create_folder("user-1", None, "资料")

        self.assertEqual(captured.exception.code, "KNOWLEDGE_NODE_NAME_CONFLICT")

    @patch("services.knowledge.knowledge_repository.get_node_depth", return_value=5)
    @patch("services.knowledge.knowledge_repository.find_owned_node", return_value={"node_type": "folder"})
    def test_create_folder_rejects_sixth_level(self, _: object, __: object) -> None:
        with self.assertRaises(DomainError) as captured:
            knowledge.create_folder("user-1", "folder-5", "过深目录")

        self.assertEqual(captured.exception.code, "KNOWLEDGE_DEPTH_LIMIT_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
