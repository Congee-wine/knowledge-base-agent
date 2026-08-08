from __future__ import annotations

from dataclasses import dataclass
import re


MAX_CHUNK_CHARACTERS = 1200
OVERLAP_CHARACTERS = 180
HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+|.+\n[-=]{3,})$", re.MULTILINE)


@dataclass(frozen=True)
class SourceText:
    content: str
    page_number: int | None


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    section_title: str | None
    paragraph_ordinal: int


def split_mixed(source_texts: list[SourceText]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for source in source_texts:
        section_title: str | None = None
        for ordinal, paragraph in enumerate(_paragraphs(source.content)):
            if _is_heading(paragraph):
                section_title = _clean_heading(paragraph)
                continue
            paragraph_chunks = _split_paragraph(paragraph, source.page_number, section_title, ordinal)
            if section_title and paragraph_chunks:
                first = paragraph_chunks[0]
                paragraph_chunks[0] = TextChunk(
                    f"{section_title}\n{first.content}",
                    first.page_number,
                    section_title,
                    first.paragraph_ordinal,
                )
            chunks.extend(paragraph_chunks)
    return chunks


def _paragraphs(content: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]


def _is_heading(paragraph: str) -> bool:
    return bool(HEADING_PATTERN.fullmatch(paragraph))


def _clean_heading(paragraph: str) -> str:
    return paragraph.splitlines()[0].lstrip("#").strip()


def _split_paragraph(paragraph: str, page_number: int | None, section_title: str | None, ordinal: int) -> list[TextChunk]:
    if len(paragraph) <= MAX_CHUNK_CHARACTERS:
        return [TextChunk(paragraph, page_number, section_title, ordinal)]
    chunks: list[TextChunk] = []
    start = 0
    while start < len(paragraph):
        end = min(len(paragraph), start + MAX_CHUNK_CHARACTERS)
        if end < len(paragraph):
            boundary = max(paragraph.rfind(mark, start, end) for mark in ("。", "！", "？", "\n", ". "))
            if boundary > start + MAX_CHUNK_CHARACTERS // 2:
                end = boundary + 1
        chunks.append(TextChunk(paragraph[start:end].strip(), page_number, section_title, ordinal))
        if end == len(paragraph):
            break
        start = max(end - OVERLAP_CHARACTERS, start + 1)
    return [chunk for chunk in chunks if chunk.content]
