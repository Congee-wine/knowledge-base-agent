from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from integrations.deepseek import create_chat_model


StrategyName = Literal["direct_answer", "knowledge_answer", "hybrid_answer", "clarify"]


@dataclass(frozen=True)
class RuntimeStrategy:
    name: StrategyName
    requires_private_evidence: bool

    @property
    def uses_knowledge(self) -> bool:
        return self.name in {"knowledge_answer", "hybrid_answer"}


_ANALYSIS_PROMPT = """你是受控智能体的任务分析器。根据用户最新问题和有限会话历史，只返回 JSON：
{"strategy":"direct_answer|knowledge_answer|hybrid_answer|clarify","requiresPrivateEvidence":true|false}

选择规则：
- 通用解释、写作、分析、建议、代码思路等不依赖用户私有资料的问题使用 direct_answer。
- 用户明确要求依据上传文档、知识库、内部制度、合同、项目资料等私有事实时使用 knowledge_answer，并将 requiresPrivateEvidence 设为 true。
- 私有资料可增强回答但仍需要通用分析或建议时使用 hybrid_answer。
- 缺少会改变结果的关键目标、对象或约束时使用 clarify。
不要把“有知识库”本身当成检索理由；不要输出解释、Markdown 或模型思维过程。"""


def decide_strategy(content: str, history: list[dict[str, str]], knowledge_available: bool) -> RuntimeStrategy:
    fallback = _fallback_strategy(content, knowledge_available)
    try:
        response = create_chat_model().invoke([
            SystemMessage(content=_ANALYSIS_PROMPT),
            HumanMessage(content=_analysis_input(content, history, knowledge_available)),
        ])
        return _parse_strategy(str(response.content), knowledge_available)
    except Exception:
        return fallback


def _analysis_input(content: str, history: list[dict[str, str]], knowledge_available: bool) -> str:
    history_text = "\n".join(f"{item['role']}: {item['content'][:800]}" for item in history[-4:])
    return f"可用私有资料范围：{'有' if knowledge_available else '无'}\n历史：\n{history_text or '无'}\n\n用户问题：{content}"


def _parse_strategy(content: str, knowledge_available: bool) -> RuntimeStrategy:
    payload = json.loads(_extract_json(content))
    name = payload.get("strategy")
    if name not in {"direct_answer", "knowledge_answer", "hybrid_answer", "clarify"}:
        raise ValueError("Invalid runtime strategy")
    if not knowledge_available and name in {"knowledge_answer", "hybrid_answer"}:
        return RuntimeStrategy("clarify" if payload.get("requiresPrivateEvidence") else "direct_answer", bool(payload.get("requiresPrivateEvidence")))
    return RuntimeStrategy(name, bool(payload.get("requiresPrivateEvidence")))


def _extract_json(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object in strategy response")
    return stripped[start:end + 1]


def _fallback_strategy(content: str, knowledge_available: bool) -> RuntimeStrategy:
    normalized = content.lower()
    private_markers = ("知识库", "资料", "文档", "上传", "合同", "制度", "内部", "手册", "项目文件")
    requests_private_evidence = any(marker in normalized for marker in private_markers)
    if requests_private_evidence and knowledge_available:
        return RuntimeStrategy("knowledge_answer", True)
    if requests_private_evidence:
        return RuntimeStrategy("clarify", True)
    return RuntimeStrategy("direct_answer", False)
