"""创建 LLM 客户端：只读 settings，缺 key 直接报错（没有离线规则兜底）。

通过 LangChain 的 `init_chat_model` 统一初始化 OpenAI 兼容协议的模型实例。
"""

from __future__ import annotations

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from .settings import settings


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """返回 DeepSeek 的 ChatModel（OpenAI 兼容协议）。

    没配 DEEPSEEK_API_KEY 就直接抛异常：本项目要求真模型，
    不提供规则版实现，避免"两套逻辑"让人读代码时分神。
    """
    if not settings.api_key:
        raise RuntimeError(
            "缺少 DEEPSEEK_API_KEY：请在仓库根目录的 .env 里填写后重试"
            "（可用 `python -m scripts.env_status` 检查是否已设置）"
        )
    return init_chat_model(
        model=settings.model,
        model_provider="openai",
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=settings.temperature,
    )