from __future__ import annotations

from typing import Literal
from dataclasses import dataclass


StrategyName = Literal["direct_answer", "knowledge_answer"]
KnowledgeOperation = Literal["none", "document_catalog", "semantic_search"]


@dataclass(frozen=True)
class RuntimeStrategy:
    name: StrategyName
    requires_private_evidence: bool
    knowledge_operation: KnowledgeOperation = "none"

    @property
    def uses_knowledge(self) -> bool:
        return self.name == "knowledge_answer"


def decide_strategy(content: str, history: list[dict[str, str]], knowledge_available: bool) -> RuntimeStrategy:
    """Select a catalog request deterministically; all other knowledge-mode requests search."""
    if not knowledge_available:
        return RuntimeStrategy("direct_answer", False)
    catalog_markers = ("哪些文件", "文件列表", "资料目录", "文档目录", "有哪些资料")
    operation: KnowledgeOperation = "document_catalog" if any(marker in content for marker in catalog_markers) else "semantic_search"
    return RuntimeStrategy("knowledge_answer", True, operation)
