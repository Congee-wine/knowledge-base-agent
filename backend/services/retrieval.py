from __future__ import annotations

from integrations.query_embeddings import embed_query
from repositories import knowledge as knowledge_repository
from retrieval.models import RetrievalSource
from services.agent_strategy import KnowledgeOperation


RECALL_LIMIT = 8
CONTEXT_LIMIT = 5


def retrieve_for_agent(user_id: str, agent_id: str, query: str) -> list[RetrievalSource]:
    normalized_query = query.strip()
    if not normalized_query:
        return []
    vector = embed_query(normalized_query)
    return knowledge_repository.search_agent_chunks(user_id, agent_id, vector, RECALL_LIMIT)[:CONTEXT_LIMIT]


def execute_knowledge_operation(
    operation: KnowledgeOperation, user_id: str, agent_id: str, query: str,
) -> list[RetrievalSource]:
    if operation == "document_catalog":
        return knowledge_repository.list_agent_documents(user_id, agent_id)
    if operation == "semantic_search":
        return retrieve_for_agent(user_id, agent_id, query)
    return []


def build_catalog_answer(sources: list[RetrievalSource]) -> str:
    if not sources:
        return "当前没有可访问且已完成索引的知识库文件。"
    lines = [f"- {source.document_name}（{_document_type(source.document_name)}）" for source in sources]
    return f"当前可访问且已完成索引的知识库文件共 {len(sources)} 份：\n" + "\n".join(lines)


def build_retrieval_context(sources: list[RetrievalSource]) -> str | None:
    if not sources:
        return None
    sections = []
    for index, source in enumerate(sources, start=1):
        location = source.to_citation()["location"] or "未定位段落"
        sections.append(f"[资料 {index}] {source.document_name}（{location}）\n{source.content}")
    return "以下资料是唯一可用的私有事实依据。只能引用其中出现的文件和内容；不得编造资料编号、文件名、分类或未检索到的事实。\n\n" + "\n\n".join(sections)


def _document_type(name: str) -> str:
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return {"md": "Markdown", "txt": "文本", "pdf": "PDF", "docx": "Word"}.get(suffix, "文件")
