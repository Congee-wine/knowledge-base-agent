from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from database import get_connection
from retrieval.models import RetrievalSource


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
