from __future__ import annotations

from dataclasses import replace
import hashlib
import logging
import re

from config import RERANK_CANDIDATE_LIMIT
from integrations.query_embeddings import embed_query, rerank_query_candidates
from repositories import knowledge, knowledge_retrieval
from retrieval.models import RetrievalSource
from services.agent_strategy import KnowledgeOperation


VECTOR_RECALL_LIMIT = 20
KEYWORD_RECALL_LIMIT = 20
CONTEXT_LIMIT = 5
DOCUMENT_CONTEXT_LIMIT = 2
DOCUMENT_LIMIT = 3
OVERVIEW_DOCUMENT_LIMIT = 30
OVERVIEW_SNIPPET_CHARACTERS = 500
RRF_K = 60
RERANK_MIN_SCORE = 0.30


logger = logging.getLogger(__name__)


def has_ready_knowledge(user_id: str, agent_id: str) -> bool:
    return knowledge_retrieval.has_ready_agent_documents(user_id, agent_id)


def has_knowledge_scope(user_id: str, agent_id: str) -> bool:
    return knowledge.has_agent_scope(user_id, agent_id)


def retrieve_for_agent(user_id: str, agent_id: str, query: str) -> list[RetrievalSource]:
    normalized_query = query.strip()
    if not normalized_query:
        return []
    vector = embed_query(normalized_query)
    vector_candidates = knowledge_retrieval.search_agent_chunks(user_id, agent_id, vector, VECTOR_RECALL_LIMIT)
    keyword_candidates = knowledge_retrieval.search_agent_chunks_by_keywords(
        user_id, agent_id, _extract_keywords(normalized_query), KEYWORD_RECALL_LIMIT,
    )
    candidates = _fuse_candidates(vector_candidates, keyword_candidates)[:RERANK_CANDIDATE_LIMIT]
    scores = rerank_query_candidates(normalized_query, [source.content for source in candidates])
    reranked = [replace(source, rerank_score=score) for source, score in zip(candidates, scores, strict=True)]
    selected = _select_context_sources(reranked)
    _record_retrieval_diagnostics(user_id, agent_id, normalized_query, reranked, selected)
    return selected


def _record_retrieval_diagnostics(
    user_id: str, agent_id: str, query: str, candidates: list[RetrievalSource], selected: list[RetrievalSource],
) -> None:
    query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
    try:
        knowledge_retrieval.record_retrieval_run(user_id, agent_id, f"sha256:{query_hash}", candidates, {source.chunk_id for source in selected})
    except Exception:
        logger.exception("failed to record retrieval diagnostics", extra={"agent_id": agent_id, "candidate_count": len(candidates)})


def _extract_keywords(query: str) -> list[str]:
    latin_tokens = re.findall(r"[A-Za-z0-9_]{2,}", query.lower())
    chinese_sequences = re.findall(r"[\u4e00-\u9fff]{2,}", query)
    chinese_terms = [
        sequence[start:end]
        for sequence in chinese_sequences
        for start in range(len(sequence))
        for end in range(start + 2, min(len(sequence), start + 6) + 1)
    ]
    ignored = {"什么", "介绍", "一下", "知识", "基本", "如何", "问题", "关于"}
    return list(dict.fromkeys(token for token in [*latin_tokens, *chinese_terms] if token not in ignored))[:20]


def _fuse_candidates(vector_candidates: list[RetrievalSource], keyword_candidates: list[RetrievalSource]) -> list[RetrievalSource]:
    candidates: dict[str, RetrievalSource] = {}
    for rank, source in enumerate(vector_candidates, start=1):
        candidates[source.chunk_id] = replace(source, vector_rank=rank, fusion_score=1 / (RRF_K + rank))
    for rank, source in enumerate(keyword_candidates, start=1):
        current = candidates.get(source.chunk_id)
        if current is None:
            candidates[source.chunk_id] = replace(source, keyword_rank=rank, fusion_score=1 / (RRF_K + rank))
            continue
        candidates[source.chunk_id] = replace(
            current, keyword_rank=rank, fusion_score=(current.fusion_score or 0) + 1 / (RRF_K + rank),
        )
    return sorted(candidates.values(), key=lambda source: source.fusion_score or 0, reverse=True)


def _select_context_sources(candidates: list[RetrievalSource]) -> list[RetrievalSource]:
    selected: list[RetrievalSource] = []
    document_counts: dict[str, int] = {}
    for source in sorted(candidates, key=lambda item: item.rerank_score or 0, reverse=True):
        if (source.rerank_score or 0) < RERANK_MIN_SCORE:
            continue
        if len(selected) >= CONTEXT_LIMIT or len(document_counts) >= DOCUMENT_LIMIT and source.document_node_id not in document_counts:
            continue
        if document_counts.get(source.document_node_id, 0) >= DOCUMENT_CONTEXT_LIMIT:
            continue
        document_counts[source.document_node_id] = document_counts.get(source.document_node_id, 0) + 1
        selected.append(source)
    return selected


def execute_knowledge_operation(
    operation: KnowledgeOperation, user_id: str, agent_id: str, query: str,
) -> list[RetrievalSource]:
    if operation == "knowledge_overview":
        return knowledge_retrieval.list_agent_documents(user_id, agent_id, OVERVIEW_DOCUMENT_LIMIT)
    if operation == "semantic_search":
        return retrieve_for_agent(user_id, agent_id, query)
    return []


def build_knowledge_overview_context(sources: list[RetrievalSource]) -> str | None:
    """Build a bounded, document-level context for a knowledge-base overview."""
    if not sources:
        return None
    sections = []
    for index, source in enumerate(sources, start=1):
        location = source.to_citation()["location"] or "未定位段落"
        snippet = source.content.strip()[:OVERVIEW_SNIPPET_CHARACTERS]
        sections.append(
            f"[资料 {index}] 文件：{source.document_name}（{_document_type(source.document_name)}，{location}）\n"
            f"代表性内容片段：{snippet}"
        )
    return (
        "以下是当前用户有权访问、且已完成索引的知识库资料概览依据。每份资料只提供一个受长度限制的代表性片段。"
        "只能依据这些文件名和片段概括，不能臆测未展示的文件内容。\n\n"
        + "\n\n".join(sections)
    )


def build_no_knowledge_answer() -> str:
    return "当前智能体资料范围内没有已完成索引的知识库文件，请先上传资料并等待索引完成。"


def build_no_match_answer() -> str:
    return "当前知识库中未找到足以回答该问题的相关内容。"


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
