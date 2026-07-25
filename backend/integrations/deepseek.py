from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT_SECONDS


class DeepSeekError(Exception):
    """Raised when the configured DeepSeek model cannot be used."""


def create_chat_model() -> ChatOpenAI:
    if not DEEPSEEK_API_KEY:
        raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        request_timeout=DEEPSEEK_TIMEOUT_SECONDS,
        streaming=True,
    )
