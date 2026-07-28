from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

from services.errors import empty_or_invalid_document, unsupported_document_type


SUPPORTED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".txt", ".md", ".markdown", ".docx"})


def validate_document_upload(filename: str, content_type: str | None, content: bytes) -> str:
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise unsupported_document_type()
    if not content:
        raise empty_or_invalid_document()
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise empty_or_invalid_document()
    if extension == ".docx" and not _is_docx(content):
        raise empty_or_invalid_document()
    if extension in {".txt", ".md", ".markdown"}:
        _validate_text_document(content)
    _validate_declared_content_type(extension, content_type)
    return extension


def _is_docx(content: bytes) -> bool:
    try:
        with ZipFile(BytesIO(content)) as archive:
            return "[Content_Types].xml" in archive.namelist() and "word/document.xml" in archive.namelist()
    except BadZipFile:
        return False


def _validate_text_document(content: bytes) -> None:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise unsupported_document_type() from error


def _validate_declared_content_type(extension: str, content_type: str | None) -> None:
    if not content_type or content_type == "application/octet-stream":
        return
    allowed_types = {
        ".pdf": {"application/pdf"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ".txt": {"text/plain"},
        ".md": {"text/markdown", "text/plain"},
        ".markdown": {"text/markdown", "text/plain"},
    }
    if content_type.lower() not in allowed_types[extension]:
        raise unsupported_document_type()
