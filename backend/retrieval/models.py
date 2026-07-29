from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalSource:
    chunk_id: str
    document_node_id: str
    document_name: str
    content: str
    page_number: int | None
    paragraph_ordinal: int | None
    section_title: str | None
    score: float
    vector_rank: int | None = None
    keyword_rank: int | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None

    def to_citation(self) -> dict[str, object]:
        location = f"第 {self.page_number} 页" if self.page_number is not None else self.section_title
        if location is None and self.paragraph_ordinal is not None:
            location = f"第 {self.paragraph_ordinal + 1} 段"
        return {"documentNodeId": self.document_node_id, "documentName": self.document_name, "location": location, "snippet": self.content[:160]}
