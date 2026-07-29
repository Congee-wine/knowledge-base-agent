from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from database import get_connection
from retrieval.models import RetrievalSource


def has_ready_agent_documents(user_id: str, agent_id: str) -> bool:
    """Return whether the agent has at least one authorized, indexed document."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE scoped_nodes AS (
                    SELECT id FROM knowledge_nodes WHERE owner_user_id = %s AND %s::uuid = '00000000-0000-0000-0000-000000000001'::uuid
                    UNION SELECT knowledge_node_id AS id FROM agent_knowledge_scopes WHERE owner_user_id = %s AND agent_id = %s
                    UNION SELECT child.id FROM knowledge_nodes AS child JOIN scoped_nodes AS parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                ) SELECT EXISTS (
                    SELECT 1 FROM document_versions AS version JOIN knowledge_nodes AS node ON node.id = version.knowledge_node_id
                    JOIN scoped_nodes AS scope ON scope.id = node.id
                    WHERE node.owner_user_id = %s AND version.is_current AND version.processing_status = 'ready'
                      AND version.index_status = 'ready'
                ) AS has_documents""",
                (user_id, agent_id, user_id, agent_id, user_id, user_id),
            )
            row = cursor.fetchone()
            return bool(row["has_documents"])


def search_agent_chunks(user_id: str, agent_id: str, vector: list[float], limit: int) -> list[RetrievalSource]:
    vector_text = "[" + ",".join(str(value) for value in vector) + "]"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE scoped_nodes AS (
                    SELECT id FROM knowledge_nodes WHERE owner_user_id = %s AND %s::uuid = '00000000-0000-0000-0000-000000000001'::uuid
                    UNION SELECT knowledge_node_id AS id FROM agent_knowledge_scopes WHERE owner_user_id = %s AND agent_id = %s
                    UNION SELECT child.id FROM knowledge_nodes AS child JOIN scoped_nodes AS parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                )
                SELECT chunk.id AS chunk_id, node.id AS document_node_id, node.name AS document_name, chunk.content,
                       chunk.page_number, chunk.metadata_json, 1 - (chunk.embedding <=> %s::vector) AS score
                FROM document_chunks AS chunk JOIN document_versions AS version ON version.id = chunk.document_version_id
                JOIN knowledge_nodes AS node ON node.id = version.knowledge_node_id JOIN scoped_nodes AS scope ON scope.id = node.id
                WHERE chunk.owner_user_id = %s AND version.is_current AND version.processing_status = 'ready'
                  AND version.index_status = 'ready' AND chunk.embedding IS NOT NULL
                ORDER BY chunk.embedding <=> %s::vector LIMIT %s""",
                (user_id, agent_id, user_id, agent_id, user_id, vector_text, user_id, vector_text, limit),
            )
            return [_to_source(row, float(row["score"])) for row in cursor.fetchall()]


def search_agent_chunks_by_keywords(user_id: str, agent_id: str, keywords: list[str], limit: int) -> list[RetrievalSource]:
    if not keywords:
        return []
    patterns = [f"%{keyword}%" for keyword in keywords]
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE scoped_nodes AS (
                    SELECT id FROM knowledge_nodes WHERE owner_user_id = %s AND %s::uuid = '00000000-0000-0000-0000-000000000001'::uuid
                    UNION SELECT knowledge_node_id AS id FROM agent_knowledge_scopes WHERE owner_user_id = %s AND agent_id = %s
                    UNION SELECT child.id FROM knowledge_nodes AS child JOIN scoped_nodes AS parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                )
                SELECT chunk.id AS chunk_id, node.id AS document_node_id, node.name AS document_name, chunk.content,
                       chunk.page_number, chunk.metadata_json,
                       cardinality(ARRAY(SELECT pattern FROM unnest(%s::text[]) AS pattern WHERE chunk.content ILIKE pattern)) AS score
                FROM document_chunks AS chunk JOIN document_versions AS version ON version.id = chunk.document_version_id
                JOIN knowledge_nodes AS node ON node.id = version.knowledge_node_id JOIN scoped_nodes AS scope ON scope.id = node.id
                WHERE chunk.owner_user_id = %s AND version.is_current AND version.processing_status = 'ready'
                  AND version.index_status = 'ready' AND chunk.content ILIKE ANY(%s::text[])
                ORDER BY score DESC, chunk.ordinal LIMIT %s""",
                (user_id, agent_id, user_id, agent_id, user_id, patterns, user_id, patterns, limit),
            )
            return [_to_source(row, float(row["score"])) for row in cursor.fetchall()]


def record_retrieval_run(
    user_id: str, agent_id: str, query_summary: str, candidates: list[RetrievalSource], selected_chunk_ids: set[str],
) -> str:
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO retrieval_runs (id, owner_user_id, agent_id, message_id, query_summary, created_at)
                   VALUES (%s, %s, %s, NULL, %s, %s)""",
                (run_id, user_id, agent_id, query_summary, now),
            )
            for rank, source in enumerate(candidates, start=1):
                selected = source.chunk_id in selected_chunk_ids
                cursor.execute(
                    """INSERT INTO retrieval_candidates
                        (id, retrieval_run_id, chunk_id, vector_rank, keyword_rank, fusion_rank, rerank_score, selected, discard_reason)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        str(uuid4()), run_id, source.chunk_id, source.vector_rank, source.keyword_rank, rank,
                        source.rerank_score, selected, None if selected else "below_threshold_or_context_limit",
                    ),
                )
        connection.commit()
    return run_id


def list_agent_documents(user_id: str, agent_id: str, limit: int = 100) -> list[RetrievalSource]:
    """Return one indexed source per document in the agent's authorized scope."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE scoped_nodes AS (
                    SELECT id FROM knowledge_nodes WHERE owner_user_id = %s AND %s::uuid = '00000000-0000-0000-0000-000000000001'::uuid
                    UNION SELECT knowledge_node_id AS id FROM agent_knowledge_scopes WHERE owner_user_id = %s AND agent_id = %s
                    UNION SELECT child.id FROM knowledge_nodes AS child JOIN scoped_nodes AS parent ON child.parent_id = parent.id WHERE child.owner_user_id = %s
                ), document_sources AS (
                    SELECT DISTINCT ON (node.id) chunk.id AS chunk_id, node.id AS document_node_id, node.name AS document_name,
                        chunk.content, chunk.page_number, chunk.metadata_json FROM document_chunks AS chunk
                    JOIN document_versions AS version ON version.id = chunk.document_version_id JOIN knowledge_nodes AS node ON node.id = version.knowledge_node_id
                    JOIN scoped_nodes AS scope ON scope.id = node.id WHERE chunk.owner_user_id = %s AND version.is_current
                      AND version.processing_status = 'ready' AND version.index_status = 'ready' AND chunk.embedding IS NOT NULL
                    ORDER BY node.id, chunk.ordinal
                ) SELECT * FROM document_sources ORDER BY document_name LIMIT %s""",
                (user_id, agent_id, user_id, agent_id, user_id, user_id, limit),
            )
            return [_to_source(row, 1.0) for row in cursor.fetchall()]


def _to_source(row: Mapping[str, Any], score: float) -> RetrievalSource:
    return RetrievalSource(
        chunk_id=str(row["chunk_id"]), document_node_id=str(row["document_node_id"]),
        document_name=str(row["document_name"]), content=str(row["content"]), page_number=row["page_number"],
        paragraph_ordinal=row["metadata_json"].get("paragraphOrdinal"), section_title=row["metadata_json"].get("sectionTitle"), score=score,
    )
