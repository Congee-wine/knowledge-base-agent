from __future__ import annotations

import unittest

from retrieval.chunking import MAX_CHUNK_CHARACTERS, SourceText, split_mixed


class ChunkingTests(unittest.TestCase):
    def test_keeps_section_and_page_metadata(self) -> None:
        chunks = split_mixed([SourceText("# Title\n\nFirst paragraph.", 3)])

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].section_title, "Title")
        self.assertEqual(chunks[0].page_number, 3)

    def test_splits_long_paragraph_with_overlap(self) -> None:
        content = "文" * (MAX_CHUNK_CHARACTERS + 200)

        chunks = split_mixed([SourceText(content, None)])

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].content[-180:], chunks[1].content[:180])


if __name__ == "__main__":
    unittest.main()
