from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from workers import tasks


class DocumentWorkerTaskTests(unittest.TestCase):
    @patch("workers.tasks.system", return_value="Linux")
    @patch("workers.tasks.get_object_storage_settings")
    @patch("workers.tasks.create_object_storage_client")
    @patch("workers.tasks.get_connection")
    def test_probe_reports_database_and_private_bucket_reachability(
        self,
        get_connection: MagicMock,
        create_client: MagicMock,
        get_settings: MagicMock,
        _: MagicMock,
    ) -> None:
        connection = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        get_settings.return_value = SimpleNamespace(bucket="ai-platform-private")
        create_client.return_value.bucket_exists.return_value = True

        result = tasks.run_document_processing_probe()

        self.assertEqual(result["database"], "ok")
        self.assertEqual(result["object_storage_bucket"], "ai-platform-private")
        connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1")
        create_client.return_value.bucket_exists.assert_called_once_with("ai-platform-private")

    @patch("workers.tasks.get_object_storage_settings")
    @patch("workers.tasks.create_object_storage_client")
    @patch("workers.tasks.get_connection")
    def test_probe_rejects_missing_private_bucket(
        self,
        get_connection: MagicMock,
        create_client: MagicMock,
        get_settings: MagicMock,
    ) -> None:
        get_settings.return_value = SimpleNamespace(bucket="ai-platform-private")
        create_client.return_value.bucket_exists.return_value = False

        with self.assertRaisesRegex(RuntimeError, "cannot find private bucket"):
            tasks.run_document_processing_probe()

        self.assertTrue(get_connection.called)


if __name__ == "__main__":
    unittest.main()
