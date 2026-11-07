"""Embedding：只用 LangChain 现成的 embedding 实现，不手写向量算法。

`OpenAIEmbeddings(model="text-embedding-v4", dimensions=1024,
 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")`
（使用 DashScope 的 OpenAI 兼容端点生成 1024 维稠密向量）

没配 key 直接报错：本项目不提供假向量兜底，避免"两套检索"分散注意力。
第一阶段粗排由 Milvus 完成（dense ANN + 内置 BM25 + 服务端 RRFRanker），第二阶段精排见 `reranker.py`。
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from ..settings import settings

_embedder: Embeddings | None = None


def get_embedder() -> Embeddings:
    """懒加载单例：缺 key 直接抛异常，提示去 .env 填。"""
    global _embedder
    if _embedder is None:
        if not settings.embedding_api_key:
            raise RuntimeError(
                "缺少 DASHSCOPE_API_KEY：请在仓库根目录的 .env 里填写后重试"
                "（可用 `python -m scripts.env_status` 检查是否已设置）"
            )
        from langchain_openai import OpenAIEmbeddings

        _embedder = OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dim,
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            check_embedding_ctx_length=False,
            # DashScope 兼容端点单次最多 10 条，超过报
            # 400 InvalidParameter: batch size is invalid, it should not be larger than 10
            chunk_size=settings.embedding_batch_size,
        )
    return _embedder
