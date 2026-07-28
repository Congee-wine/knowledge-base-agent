from __future__ import annotations

from integrations.query_embeddings import embed_query
from repositories import knowledge as knowledge_repository
from retrieval.models import RetrievalSource


RECALL_LIMIT = 8
CONTEXT_LIMIT = 5


def retrieve_for_agent(user_id: str, agent_id: str, query: str) -> list[RetrievalSource]:
    normalized_query = query.strip()
    if not normalized_query:
        return []
    vector = embed_query(normalized_query)
    return knowledge_repository.search_agent_chunks(user_id, agent_id, vector, RECALL_LIMIT)[:CONTEXT_LIMIT]


def build_retrieval_context(sources: list[RetrievalSource]) -> str | None:
    if not sources:
        return None
    sections = []
    for index, source in enumerate(sources, start=1):
        location = source.to_citation()["location"] or "未定位段落"
        sections.append(f"[资料 {index}] {source.document_name}（{location}）\n{source.content}")
    return "以下资料仅供回答当前问题；没有依据时请明确说明。\n\n" + "\n\n".join(sections)
