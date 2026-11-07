"""Cross-Encoder 精排层（Reranker）：RRF 粗排之后的第二阶段相关性重打分。

为什么在 `Dense + BM25 + RRF` 之后还需要精排：
1. 第一阶段（双塔向量 + BM25）各自独立编码，缺少 query 与 chunk 之间的 token 级交叉注意力；
2. RRF（`1/(60+rank)`）只看名次不看分数，当用户使用口语指代（如"用掉的"对应制度里的"已消耗"、
   "别的子公司"对应"跨租户"）时，BM25 容易被"退款""工单"等高频表面词吸走，把真正命中的小节挤到第 4~10 名；
3. 二级漏斗：先由 Milvus 服务端 RRF 快速融合出 Top-10 粗排候选，再送入 DashScope `gte-rerank-v2`
   做 Cross-Encoder 交叉注意力精排取最终 Top-K，兼顾召回率、首位精度与延迟（云端精排 ~100ms）。

高可用原则（优雅降级）：
- 直接复用 `DASHSCOPE_API_KEY` 与标准 `httpx` 连接池，零新增重依赖（不往本地塞 2GB PyTorch 模型）；
- 若精排被关闭、未配 Key、网络超时或返回异常，自动退回 RRF 粗排前 K 条，绝不阻塞主链路。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..settings import settings

logger = logging.getLogger(__name__)

_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    """复用长连接池，省掉每次精排的 TLS 握手开销（可省 40~80ms）。"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=settings.rerank_timeout)
    return _http_client


def _doc_text(hit: dict[str, Any]) -> str:
    """拼装送进 Cross-Encoder 的文本：带上文档与章节面包屑（若正文中尚未包含），帮助模型理解制度语境。"""
    content = str(hit.get("content") or "").strip()
    citation = str(hit.get("citation") or "").strip()
    if citation and citation not in content:
        return f"{citation}\n{content}"
    return content


def rerank_hits(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 3,
    alpha: float = 0.5,
) -> list[dict[str, Any]]:
    """用 DashScope `gte-rerank-v2` 对 RRF 粗排候选做 Cross-Encoder 精排，并与 RRF 粗排分做归一化融合，返回前 `top_k` 条。

    为什么要做 `alpha * norm(ce_score) + (1 - alpha) * norm(rrf_score)` 融合：
    - Cross-Encoder 擅长捕捉深层语义指代（如"用掉的"→"已消耗"），但对纯术语精确匹配（如"事前申请"）有时会被高频词稀释；
    - 保留 RRF（Dense+BM25）与 Cross-Encoder 的双阶段归一化加权融合（默认 alpha=0.5），既能把 g33 等口语指代拉进 Top-3，
      又不会丢失 RRF 在精确词面匹配上的高置信排序。

    异常或未启用时原样截断返回 `candidates[:top_k]`（保留 RRF 排序）。
    """
    if not candidates:
        return []
    if not settings.rerank_active or len(candidates) <= 1:
        return candidates[:top_k]

    documents = [_doc_text(item) for item in candidates]
    payload = {
        "model": settings.rerank_model,
        "input": {
            "query": query,
            "documents": documents,
        },
        "parameters": {
            "top_n": len(candidates),
            "return_documents": False,
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.rerank_api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = _get_http_client().post(settings.rerank_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        results = (data.get("output") or {}).get("results") or []
        if not results:
            logger.warning("精排返回空结果，自动回退 RRF 粗排顺序")
            return candidates[:top_k]

        scored: list[dict[str, Any]] = []
        for item in results:
            idx = int(item.get("index", -1))
            if 0 <= idx < len(candidates):
                row = dict(candidates[idx])
                row["rrf_score"] = float(row.get("score") or 0.0)
                row["rerank_score"] = round(float(item.get("relevance_score") or 0.0), 4)
                row["channel"] = "hybrid+rerank"
                scored.append(row)

        if not scored:
            return candidates[:top_k]

        rrf_vals = [r["rrf_score"] for r in scored]
        ce_vals = [r["rerank_score"] for r in scored]
        r_min, r_max = min(rrf_vals), max(rrf_vals)
        c_min, c_max = min(ce_vals), max(ce_vals)

        for r in scored:
            r_norm = (r["rrf_score"] - r_min) / (r_max - r_min + 1e-9)
            c_norm = (r["rerank_score"] - c_min) / (c_max - c_min + 1e-9)
            r["score"] = round(alpha * c_norm + (1.0 - alpha) * r_norm, 4)

        scored.sort(key=lambda x: (x["score"], x["rerank_score"], x["rrf_score"]), reverse=True)
        return scored[:top_k]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cross-Encoder 精排不可用（%s: %s），自动降级为 RRF 粗排结果", type(exc).__name__, exc)
        return candidates[:top_k]
