from __future__ import annotations

from typing import Literal
from dataclasses import dataclass


StrategyName = Literal["direct_answer", "knowledge_answer"]
KnowledgeOperation = Literal["none", "knowledge_overview", "semantic_search"]


@dataclass(frozen=True)
class RuntimeStrategy:
    name: StrategyName
    requires_private_evidence: bool
    knowledge_operation: KnowledgeOperation = "none"

    @property
    def uses_knowledge(self) -> bool:
        return self.name == "knowledge_answer"


def decide_strategy(content: str, history: list[dict[str, str]], knowledge_available: bool) -> RuntimeStrategy:
    """Route knowledge-base overview requests separately from fact retrieval."""
    if not knowledge_available:
        return RuntimeStrategy("direct_answer", False)
    overview_markers = (
        "哪些文件", "文件列表", "资料目录", "文档目录", "知识库目录", "有哪些资料",
        "知识库有什么", "这个知识库有什么", "能回答什么", "可以回答什么",
    )
    operation: KnowledgeOperation = "knowledge_overview" if any(marker in content for marker in overview_markers) else "semantic_search"
    return RuntimeStrategy("knowledge_answer", True, operation)
