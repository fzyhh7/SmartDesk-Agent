"""知识库入口：只走 Milvus，没有本地兜底。

分层（面试可讲）：节点只认这里的函数名；换 pgvector / ES 只改这一层与 rag/vector_store.py。
检索采用二级漏斗：
1) 粗排召回：Milvus 服务端 dense（1024 维 COSINE）+ sparse（内置 BM25）双路召回，经 `RRFRanker(k=60)` 融合出 Top-10 候选；
2) 精排重排：DashScope `gte-rerank-v2`（Cross-Encoder）对候选做交叉注意力重打分取最终 Top-K（异常自动降级回 RRF）。

知识从哪来：`docs/kb/pdf` 的公开制度文档 → MinerU 解析成 Markdown（`rag/pdf_parser.py`）
→ 结构感知切分（`rag/splitter.py`）→ 本模块 `ingest()` 写进 Milvus。
Milvus 或 embedding 不可用就直接抛错（`MilvusUnavailable`）——
"检索不到"和"检索服务挂了"是两种事故，不能混成一个空列表。
"""

from __future__ import annotations

import logging
from typing import Any

from .rag import vector_store
from .rag.splitter import Chunk
from .settings import settings

logger = logging.getLogger(__name__)

DEFAULT_TENANT = settings.default_tenant

_ready = False


class MilvusUnavailable(RuntimeError):
    """Milvus 连不上、collection 不可用，或者知识库还没入库。"""


def ensure_ready() -> None:
    """第一次检索前确认 collection 存在且非空；不自动造数据（知识库只接受真实文档）。"""
    global _ready
    if _ready:
        return
    try:
        stats = vector_store.collection_stats()
    except Exception as exc:  # noqa: BLE001
        raise MilvusUnavailable(
            f"Milvus 不可用（{type(exc).__name__}: {exc}）。"
            "请先 `cd deploy && docker compose up -d`，再用 `python -m scripts.env_status` 看配置。"
        ) from exc
    if not stats["exists"] or stats["rows"] == 0:
        raise MilvusUnavailable(
            "知识库是空的。先入库一次："
            "`python -m scripts.ingest_docs --md docs/kb/md --to-milvus`"
        )
    _ready = True


def search(
    query: str,
    k: int = 3,
    tenant_id: str | None = None,
    *,
    rerank: bool | None = None,
) -> list[dict[str, Any]]:
    """知识库检索：dense + BM25 两路召回 → 服务端 RRF 粗排 → Cross-Encoder 精排。"""
    ensure_ready()
    return vector_store.hybrid_search(query, k=k, tenant_id=tenant_id, rerank=rerank)


def ingest(
    chunks: list[Chunk],
    *,
    tenant_id: str | None = None,
    force: bool = False,
) -> int:
    """把切分好的 chunk 写进 Milvus（`--to-milvus` 调这里；force 会重建 collection）。"""
    global _ready
    count = vector_store.upsert_chunks(chunks, tenant_id=tenant_id, force=force)
    _ready = count > 0
    logger.info("知识库入库完成：%s 条 chunk，租户=%s", count, tenant_id or DEFAULT_TENANT)
    return count


def publish_article(
    *,
    title: str,
    content: str,
    tags: str = "",
    change_note: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """发布一篇知识文章（kb-server 的 publish_kb_article 落到这里）。"""
    ensure_ready()
    return vector_store.publish_article(
        title=title,
        content=content,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        change_note=change_note,
        tenant_id=tenant_id or DEFAULT_TENANT,
    )


def health() -> dict[str, Any]:
    """健康检查：连得上、collection 存在、有几行。"""
    stats = vector_store.collection_stats()
    return {"backend": "milvus", "collection": stats["collection"], "rows": stats["rows"]}


__all__ = [
    "DEFAULT_TENANT",
    "MilvusUnavailable",
    "ensure_ready",
    "health",
    "ingest",
    "publish_article",
    "search",
]
