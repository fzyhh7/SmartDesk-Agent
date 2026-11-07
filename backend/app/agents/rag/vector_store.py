"""Milvus 数据层：混合检索粗排（Dense + 内置 BM25 + RRF）+ Cross-Encoder 精排二级漏斗。

核心设计：
- Schema：dim=1024 的 FLOAT_VECTOR（稠密）+ SPARSE_FLOAT_VECTOR（稀疏）
- 内置 BM25：Function(function_type=FunctionType.BM25)，由 Milvus 服务端算稀疏向量
- 索引：dense = AUTOINDEX + COSINE；sparse = SPARSE_INVERTED_INDEX + BM25
- 二级检索漏斗：
  1) 粗排召回：`client.hybrid_search(reqs=[...], ranker=RRFRanker(k=60))` 融合出 Top-10 候选；
  2) 精排重排：DashScope `gte-rerank-v2`（Cross-Encoder）对候选交叉打分取最终 Top-K（异常自动降级回 RRF）。
- 标量过滤：tenant_id == "..."，多租户隔离靠 filter 而不是靠多个 collection

为什么直接用 pymilvus 原生 API 而不是 langchain_milvus 封装：
原生 MilvusClient 能直接调用服务端内置 BM25 Function 与双路 AnnSearchRequest + RRFRanker，
链路清晰透明，避免高层封装隐藏混合检索参数。
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from pymilvus import (
    AnnSearchRequest,
    DataType,
    Function,
    FunctionType,
    MilvusClient,
    RRFRanker,
)

from ..settings import settings
from .embedding import get_embedder
from .reranker import rerank_hits
from .splitter import Chunk, make_citation

logger = logging.getLogger(__name__)

DENSE_FIELD = "dense"
SPARSE_FIELD = "sparse"
TEXT_FIELD = "content"
BM25_FUNCTION = "content_bm25"
# 库里只有一种状态：发布过才算存在（写入前必过审批闸门，没有草稿态）
DOC_STATUS_PUBLISHED = "published"
# collection 结构版本标记：缺这个字段说明是老库（旧 schema），自动重建
SCHEMA_MARKER = "source_file"
# 检索结果回传的标量字段（引用角标 + 溯源用）
OUTPUT_FIELDS = [
    "doc_id",
    "title",
    "h1",
    "h2",
    "h3",
    "source_file",
    "chunk_index",
    "content",
    "doc_status",
]

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=settings.milvus_uri, timeout=settings.milvus_timeout)
    return _client


def reset_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:  # pragma: no cover
            pass
    _client = None


def _filter_expr(tenant_id: str | None) -> str:
    """过滤表达式：多租户隔离 + 只检索已发布内容。

    写入侧只有两条路（`upsert_chunks` 入库文档、`publish_article` 发布文章），
    而发布本身要过审批闸门，所以落库时一定已经是 published，库里没有草稿态。
    这里仍保留 `doc_status` 过滤，是把它当"可见性不变量"写在读路径上：
    将来若有人加一条绕过审批的写入旁路，默认也不会把未发布内容漏给员工。
    """
    parts: list[str] = []
    if tenant_id:
        parts.append(f'tenant_id == "{tenant_id}"')
    parts.append('doc_status == "published"')
    return " and ".join(parts)


def ensure_collection(drop: bool = False, client: MilvusClient | None = None) -> MilvusClient:
    """建 collection：字段 + 内置 BM25 函数 + 三个索引。已存在则直接返回。"""
    client = client or get_client()
    name = settings.milvus_collection

    if client.has_collection(name):
        if not drop:
            fields = [f.get("name") for f in (client.describe_collection(name).get("fields") or [])]
            if SCHEMA_MARKER in fields:
                return client
            logger.warning("collection %s 是旧 schema（缺 %s），自动重建", name, SCHEMA_MARKER)
        client.drop_collection(name)
        logger.info("已删除旧 collection %s", name)

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("pk", DataType.INT64, is_primary=True)
    schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
    # 多租户隔离：每行带 tenant_id，检索时用 filter 表达式过滤
    schema.add_field("tenant_id", DataType.VARCHAR, max_length=64)
    schema.add_field("title", DataType.VARCHAR, max_length=512)
    # 章节三层：h1=第 X 章、h2=X.Y 节、h3=更深一级；引用串就用这三层拼
    schema.add_field("h1", DataType.VARCHAR, max_length=128)
    schema.add_field("h2", DataType.VARCHAR, max_length=128)
    schema.add_field("h3", DataType.VARCHAR, max_length=128)
    # 溯源字段：这个块来自哪个文件、是第几块（重跑入库靠它们幂等覆盖）
    schema.add_field(SCHEMA_MARKER, DataType.VARCHAR, max_length=256)
    schema.add_field("chunk_index", DataType.INT64)
    # 开启中文分词器，BM25 才知道怎么切 "增值税发票"
    schema.add_field(
        TEXT_FIELD,
        DataType.VARCHAR,
        max_length=8192,
        enable_analyzer=True,
        analyzer_params={"type": "chinese"},
    )
    # 可见性标记：库里只会写 published（发布前必过审批闸门），保留该字段是为了让读路径能把它当不变量来断言
    schema.add_field("doc_status", DataType.VARCHAR, max_length=16)
    schema.add_field(DENSE_FIELD, DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
    schema.add_field(SPARSE_FIELD, DataType.SPARSE_FLOAT_VECTOR)
    # 内置 BM25：Milvus 服务端把 content 算成稀疏向量写进 sparse 字段
    schema.add_function(
        Function(
            name=BM25_FUNCTION,
            input_field_names=[TEXT_FIELD],
            output_field_names=[SPARSE_FIELD],
            function_type=FunctionType.BM25,
        )
    )

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name=DENSE_FIELD, index_type="AUTOINDEX", metric_type="COSINE"
    )
    index_params.add_index(
        field_name=SPARSE_FIELD, index_type="SPARSE_INVERTED_INDEX", metric_type="BM25"
    )
    # 标量索引用 INVERTED：tenant_id / source_file 过滤 + doc_id 精确查
    index_params.add_index(field_name="tenant_id", index_type="INVERTED")
    index_params.add_index(field_name="doc_id", index_type="INVERTED")
    index_params.add_index(field_name=SCHEMA_MARKER, index_type="INVERTED")
    index_params.add_index(field_name="doc_status", index_type="INVERTED")

    client.create_collection(
        collection_name=name, schema=schema, index_params=index_params
    )
    logger.info("已创建 collection %s（dim=%s）", name, settings.embedding_dim)
    return client


def _chunk_pk(tenant_id: str, doc_id: str, chunk_index: int) -> int:
    """主键：租户 + 文档 + 块序号 的稳定哈希。

    auto_id=False 时主键要自己给；用稳定哈希保证「重复入库 = 覆盖同一行」，
    不会每次 ingest 都往库里堆一份重复 chunk。
    """
    digest = hashlib.sha1(f"{tenant_id}:{doc_id}:{chunk_index}".encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def upsert_chunks(
    chunks: list[Chunk],
    *,
    tenant_id: str | None = None,
    force: bool = False,
) -> int:
    """把切分好的 chunk 写进 Milvus（幂等 upsert）。

    - dense：用 `chunk.text`（正文已带「文档 · 章节」面包屑）算 embedding；
    - sparse：不传，由 collection 上的内置 BM25 函数在服务端生成；
    - `force=True` 会 drop 重建 collection（改 schema / 换 embedding 模型时用）。

    落库一律 `doc_status="published"`：本文档库入库的是已定稿的制度文件，没有草稿态。
    """
    tenant_id = tenant_id or settings.default_tenant
    if not chunks:
        return 0
    client = ensure_collection(drop=force)
    embedder = get_embedder()
    vectors = embedder.embed_documents([chunk.text for chunk in chunks])
    rows: list[dict[str, Any]] = []
    for chunk, vector in zip(chunks, vectors):
        meta = chunk.metadata
        doc_id = str(meta.get("doc_id", ""))
        chunk_index = int(meta.get("chunk_index", 0))
        rows.append(
            {
                "pk": _chunk_pk(tenant_id, doc_id, chunk_index),
                "doc_id": doc_id,
                "tenant_id": tenant_id,
                "title": str(meta.get("title", ""))[:500],
                "h1": str(meta.get("h1", ""))[:120],
                "h2": str(meta.get("h2", ""))[:120],
                "h3": str(meta.get("h3", ""))[:120],
                SCHEMA_MARKER: str(meta.get("source_file", ""))[:240],
                "chunk_index": chunk_index,
                # 存「带面包屑的正文」：BM25 也能吃到章节词，回答引用更准
                "content": chunk.text[:8000],
                "doc_status": DOC_STATUS_PUBLISHED,
                DENSE_FIELD: vector,
            }
        )
    client.upsert(collection_name=settings.milvus_collection, data=rows)
    client.flush(settings.milvus_collection)
    # 刚写入的数据要先被索引成可检索 segment，稍等一下再检索（否则第一问会“查不到”）
    time.sleep(1.2)
    return len(rows)


def collection_stats() -> dict[str, Any]:
    """集合概况。

    `rows` 用 `count(*)` 查真实可见行，而不是 `get_collection_stats().row_count`：
    后者统计的是已写入的行，delete 之后要等 Milvus 自己 compact 才会减少，
    演示时会出现"删了文章但 health 还多几行"的怪现象。
    """
    client = get_client()
    name = settings.milvus_collection
    if not client.has_collection(name):
        return {"collection": name, "exists": False, "rows": 0}
    result = client.query(collection_name=name, filter="", output_fields=["count(*)"])
    rows = int((result[0] or {}).get("count(*)", 0)) if result else 0
    return {"collection": name, "exists": True, "rows": rows}


def _hit_row(hit: dict[str, Any], channel: str) -> dict[str, Any]:
    """把 Milvus 的一条命中摊平成业务字段（含现成的引用串）。"""
    entity = hit.get("entity") or {}
    title = str(entity.get("title", ""))
    h1 = str(entity.get("h1", ""))
    h2 = str(entity.get("h2", ""))
    h3 = str(entity.get("h3", ""))
    return {
        "doc_id": str(entity.get("doc_id", "")),
        "title": title,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "citation": make_citation(title, h1, h2, h3) or str(entity.get(SCHEMA_MARKER, "")),
        "source_file": str(entity.get(SCHEMA_MARKER, "")),
        "chunk_index": int(entity.get("chunk_index") or 0),
        "content": str(entity.get("content", "")),
        "score": round(float(hit.get("distance") or 0.0), 4),
        "doc_status": str(entity.get("doc_status", DOC_STATUS_PUBLISHED)),
        "channel": channel,
    }


def hybrid_search(
    query: str,
    k: int = 3,
    tenant_id: str | None = None,
    *,
    rerank: bool | None = None,
) -> list[dict[str, Any]]:
    """二级检索漏斗：Milvus 服务端双路召回 + RRF 粗排 → Cross-Encoder 精排。

    1. 第一阶段（Milvus 服务端一次 RPC）：
       - 两路召回：`AnnSearchRequest(dense, metric=COSINE)` + `AnnSearchRequest(sparse, metric=BM25)`；
       - RRF 粗排：`RRFRanker(k=60)` 融合出 `candidate_k`（默认 max(k, 10)）条候选；
    2. 第二阶段（Cross-Encoder 精排）：
       - 若启用精排（`rerank=True` 或默认跟随 `settings.rerank_active`），调用 `gte-rerank-v2`
         对候选集做 query-chunk 交叉注意力打分并截断至 `k` 条；
       - 若关闭精排或精排接口超时异常，直接返回 RRF 粗排前 `k` 条。
    """
    use_rerank = settings.rerank_active if rerank is None else (rerank and bool(settings.rerank_api_key))
    candidate_k = max(k, settings.rerank_candidate_k) if use_rerank else k
    per_channel_limit = max(candidate_k * 2, 15) if use_rerank else max(k * 2, 10)

    client = ensure_collection()
    expr = _filter_expr(tenant_id)
    vector = get_embedder().embed_query(query)
    reqs = [
        AnnSearchRequest(
            data=[vector],
            anns_field=DENSE_FIELD,
            param={"metric_type": "COSINE"},
            limit=per_channel_limit,
            expr=expr,
        ),
        AnnSearchRequest(
            data=[query],
            anns_field=SPARSE_FIELD,
            param={"metric_type": "BM25"},
            limit=per_channel_limit,
            expr=expr,
        ),
    ]
    results = client.hybrid_search(
        collection_name=settings.milvus_collection,
        reqs=reqs,
        ranker=RRFRanker(k=60),
        limit=candidate_k,
        output_fields=OUTPUT_FIELDS,
    )
    candidates = [_hit_row(hit, "hybrid") for hit in (results[0] if results else [])]
    if use_rerank:
        return rerank_hits(query, candidates, top_k=k)
    return candidates[:k]


def publish_article(
    *,
    title: str,
    content: str,
    tags: list[str] | None = None,
    change_note: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """把一篇知识文章写进 Milvus（供 kb-server 的 publish_kb_article 调用）。

    人工发布不走文档切分，所以只有一块；pk 依旧用稳定的哈希，
    同一篇文章重复发布不会插两行（这里用毫秒时间戳做后缀，保证「每次发布算一篇新文章」）。
    """
    tenant_id = tenant_id or settings.default_tenant
    client = ensure_collection()
    doc_id = f"kb-{int(time.time() * 1000)}"
    tags = tags or []
    text = f"【{make_citation(title, tags[0] if tags else '', change_note)}】\n{content}"
    row = {
        "pk": _chunk_pk(tenant_id, doc_id, 0),
        "doc_id": doc_id,
        "tenant_id": tenant_id,
        "title": title[:200],
        "h1": (tags[0] if tags else "知识沉淀")[:60],
        "h2": (change_note or (tags[-1] if tags else ""))[:60],
        "h3": "",
        SCHEMA_MARKER: f"{doc_id}.md",
        "chunk_index": 0,
        "content": text[:8000],
        "doc_status": DOC_STATUS_PUBLISHED,
        DENSE_FIELD: get_embedder().embed_query(text),
    }
    client.upsert(collection_name=settings.milvus_collection, data=[row])
    client.flush(settings.milvus_collection)
    return {
        "doc_id": doc_id,
        "title": title,
        "doc_status": DOC_STATUS_PUBLISHED,
        "tenant_id": tenant_id,
    }


def ping() -> bool:
    """健康检查：连得上并且 collection 存在才算 ready。"""
    try:
        client = get_client()
        return bool(client.has_collection(settings.milvus_collection))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Milvus 不可用: %s", exc)
        return False