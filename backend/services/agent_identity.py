from __future__ import annotations

from dataclasses import dataclass
import re


_SENSITIVE_MODEL_TERMS = re.compile(
    r"\b(deepseek|openai|chatgpt|gpt(?:[- ]?\d[\w.-]*)?|claude|gemini|llm)\b|"
    r"\b(?:what|which|underlying)\s+model\b|\bmodel\s+are\s+you\b|\bknowledge\s+cutoff\b|"
    r"模型(?:是什么|版本|名称|厂商|供应商)?|底层(?:模型|技术)|"
    r"知识(?:截止|更新)(?:时间|日期)?|训练数据|系统提示词|提示词|api\s*(?:key|密钥)",
    re.IGNORECASE,
)
_IDENTITY_TERMS = re.compile(r"你是谁|你能做什么|你的职责|介绍一下你自己|what are you|who are you|what can you do", re.IGNORECASE)
_SELF_DISCLOSURE = re.compile(r"(?:我是|我使用|底层(?:使用|调用)|模型(?:是|为)|知识截止).{0,40}(?:deepseek|openai|chatgpt|gpt|claude|gemini|版本|截止)", re.IGNORECASE)


@dataclass(frozen=True)
class AgentPublicProfile:
    name: str
    role: str
    knowledge_base_available: bool


def build_public_profile(name: str | None, description: str | None, knowledge_base_available: bool) -> AgentPublicProfile:
    return AgentPublicProfile(
        name=(name or "AI 管家").strip() or "AI 管家",
        role=(description or "帮助你分析问题、整理内容，并在已授权资料可用时提供基于资料的回答。").strip(),
        knowledge_base_available=knowledge_base_available,
    )


def requires_public_profile_answer(content: str) -> bool:
    return bool(_SENSITIVE_MODEL_TERMS.search(content) or _IDENTITY_TERMS.search(content))


def render_public_profile_answer(profile: AgentPublicProfile, content: str) -> str:
    if _SENSITIVE_MODEL_TERMS.search(content):
        return f"我是{profile.name}。{profile.role} 我不能提供内部技术配置，但可以说明当前可用功能和回答依据。"
    knowledge_text = "可在已授权资料可用时参考知识库内容回答。" if profile.knowledge_base_available else "当前会根据你的问题提供文本问答与分析。"
    return f"我是{profile.name}。{profile.role} {knowledge_text} 当前不提供联网搜索、对话附件处理或表格文件处理。"


def contains_self_disclosure(answer: str) -> bool:
    return bool(_SELF_DISCLOSURE.search(answer))
