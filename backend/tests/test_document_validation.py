from __future__ import annotations

import unittest
from io import BytesIO
from zipfile import ZipFile

from services.document_validation import validate_document_upload
from services.errors import DomainError


def make_docx() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
    return output.getvalue()


class DocumentValidationTests(unittest.TestCase):
    def test_accepts_supported_documents_with_valid_content(self) -> None:
        self.assertEqual(validate_document_upload("a.pdf", "application/pdf", b"%PDF-1.7\n"), ".pdf")
        self.assertEqual(validate_document_upload("a.md", "text/markdown", b"# title"), ".md")
        self.assertEqual(validate_document_upload("a.docx", None, make_docx()), ".docx")

    def test_rejects_unsupported_extension_or_invalid_signature(self) -> None:
        for filename, content in [("a.png", b"image")]:
            with self.subTest(filename=filename), self.assertRaises(DomainError) as captured:
                validate_document_upload(filename, None, content)
            self.assertEqual(captured.exception.code, "UNSUPPORTED_DOCUMENT_TYPE")

    def test_rejects_empty_or_invalid_pdf_and_docx_with_specific_error(self) -> None:
        for filename, content in [("empty.docx", b""), ("a.pdf", b"not a pdf"), ("a.docx", b"not a zip")]:
            with self.subTest(filename=filename), self.assertRaises(DomainError) as captured:
                validate_document_upload(filename, None, content)
            self.assertEqual(captured.exception.code, "EMPTY_OR_INVALID_DOCUMENT")
