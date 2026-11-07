"""RAG 评测：拿 golden set 跑检索指标（支持 RRF 粗排 vs RRF+Rerank 精排 A/B 对照），可选跑真实回答统计引用准确率。

用法：
    python -m scripts.eval_rag                  # 默认评 RRF + Cross-Encoder 精排
    python -m scripts.eval_rag --compare        # 同时跑纯 RRF 与 RRF+Rerank，生成 A/B 对照表
    python -m scripts.eval_rag --no-rerank      # 强制关闭精排，仅评纯 RRF 粗排
    python -m scripts.eval_rag --answers 20     # 额外跑 20 条完整链路，统计引用准确率与延迟
    python -m scripts.eval_rag --top-k 5        # 改检索条数

golden set 的每条用例长这样（按「文档 + 小节」标注，换 embedding/rerank 模型也不用改）：
    {"id": "g01", "query": "...", "tenant_id": "tenant-demo",
     "expected_source": "01-员工手册.md", "expected_section": "3.1 年假", "must_include": "年假"}

产出：
    docs/eval/report.md（表格 + A/B 对照数字，可直接复现）
    stdout 一行 JSON（方便 CI / 复现）
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agents import knowledge  # noqa: E402
from backend.app.agents.settings import settings  # noqa: E402

GOLDEN = ROOT_DIR / "docs" / "eval" / "golden_set.jsonl"
REPORT = ROOT_DIR / "docs" / "eval" / "report.md"


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _where(chapter: str = "", section: str = "") -> str:
    return " · ".join(part for part in (chapter, section) if part)


def _pick(row: dict[str, Any], *names: str) -> str:
    """同一含义在不同层叫法不同：向量库命中是 h2/h3，Agent 的 evidence 是 chapter/section。"""
    for name in names:
        value = row.get(name)
        if value:
            return str(value)
    return ""


def _hit_label(hit: dict[str, Any]) -> str:
    """命中块的可读标签：01-员工手册.md · 3.1 年假"""
    chapter = _pick(hit, "h2", "chapter")
    section = _pick(hit, "h3", "section")
    return f"{_pick(hit, 'source_file') or '?'} · {_where(chapter, section)}".strip()


def _hit_matches(hit: dict[str, Any], case: dict[str, Any]) -> bool:
    """命中判定：同一个源文件 + 命中块的章节里出现期望小节（如 3.1 年假）。"""
    if _pick(hit, "source_file") != case["expected_source"]:
        return False
    heading = _pick(hit, "h2", "chapter") + _pick(hit, "h3", "section")
    return case["expected_section"] in heading


def evaluate_retrieval(
    cases: list[dict[str, Any]],
    top_k: int,
    *,
    rerank: bool | None = None,
) -> dict[str, Any]:
    use_rerank = settings.rerank_active if rerank is None else (rerank and bool(settings.rerank_api_key))
    # 预热一次：首次搜索要等 Milvus 载入内存 & HTTP 连接池建连，不能算进延迟统计
    knowledge.search(cases[0]["query"], k=top_k, tenant_id=cases[0]["tenant_id"], rerank=use_rerank)

    rows: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        try:
            hits = knowledge.search(
                case["query"],
                k=top_k,
                tenant_id=case["tenant_id"],
                rerank=use_rerank,
            )
        except knowledge.MilvusUnavailable as exc:
            print(f"[FATAL] 知识库不可用：{exc}")
            raise SystemExit(2)
        latency_ms = (time.perf_counter() - started) * 1000
        rank = next((i + 1 for i, hit in enumerate(hits) if _hit_matches(hit, case)), None)
        top1_text = (hits[0].get("content", "") + hits[0].get("title", "")) if hits else ""
        rows.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected": f"{case['expected_source']} · {case['expected_section']}",
                "got": [_hit_label(hit) for hit in hits],
                "rank": rank,
                "hit1": rank == 1,
                "hitk": rank is not None,
                "keyword_hit": case["must_include"] in top1_text,
                "latency_ms": latency_ms,
            }
        )

    total = len(rows)
    summary = {
        "mode": f"hybrid+rerank({settings.rerank_model})" if use_rerank else "hybrid(RRF)",
        "rerank": use_rerank,
        "cases": total,
        "top_k": top_k,
        "recall@1": round(sum(r["hit1"] for r in rows) / total, 4),
        "recall@k": round(sum(r["hitk"] for r in rows) / total, 4),
        "mrr@k": round(sum((1.0 / r["rank"]) if r["rank"] else 0.0 for r in rows) / total, 4),
        "top1_keyword_rate": round(sum(r["keyword_hit"] for r in rows) / total, 4),
        "latency_ms_avg": round(statistics.mean(r["latency_ms"] for r in rows), 1),
        "latency_ms_p95": round(sorted(r["latency_ms"] for r in rows)[max(0, int(total * 0.95) - 1)], 1),
    }
    return {"rows": rows, "summary": summary}


def evaluate_answers(cases: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    """跑真实主图（真模型）：引用里是否包含期望文档的期望小节。"""
    from backend.app.agents.graph import get_graph
    from backend.app.agents.state import UserContext, initial_state

    graph = get_graph()
    context = UserContext(user_id="u-1001", tenant_id="tenant-demo", roles=("employee",))
    rows: list[dict[str, Any]] = []
    for case in cases[:limit]:
        thread_id = f"eval-{uuid.uuid4().hex[:8]}"
        started = time.perf_counter()
        payload = initial_state(
            tenant_id=case["tenant_id"],
            user_id="u-1001",
            query=case["query"],
            thread_id=thread_id,
        )
        try:
            result = graph.invoke(
                payload,
                {"configurable": {"thread_id": thread_id}},
                context=context,
            )
        except Exception as exc:  # 单条失败不影响整体
            rows.append({"id": case["id"], "query": case["query"], "error": str(exc)})
            continue
        elapsed = time.perf_counter() - started
        evidence = result.get("policy_evidence") or []
        cited = [_hit_label(item) for item in evidence]
        reply = result.get("reply") or ""
        rows.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected": f"{case['expected_source']} · {case['expected_section']}",
                "cited": cited,
                "citation_ok": any(_hit_matches(item, case) for item in evidence),
                "has_citation_text": "[1]" in reply or "[2]" in reply or "[3]" in reply,
                "keyword_in_reply": case["must_include"] in reply,
                "outcome": result.get("outcome"),
                "via": result.get("via"),
                "elapsed_s": round(elapsed, 2),
            }
        )

    ok = [r for r in rows if "error" not in r]
    total = max(1, len(ok))
    summary = {
        "answer_cases": len(rows),
        "answer_errors": len(rows) - len(ok),
        "citation_accuracy": round(sum(r["citation_ok"] for r in ok) / total, 4),
        "citation_mark_rate": round(sum(r["has_citation_text"] for r in ok) / total, 4),
        "keyword_in_reply_rate": round(sum(r["keyword_in_reply"] for r in ok) / total, 4),
        "elapsed_s_avg": round(statistics.mean(r["elapsed_s"] for r in ok), 2) if ok else 0,
        "elapsed_s_p95": round(sorted(r["elapsed_s"] for r in ok)[max(0, int(total * 0.95) - 1)], 2) if ok else 0,
    }
    return {"rows": rows, "summary": summary}


def write_report(
    retrieval: dict[str, Any],
    answers: dict[str, Any] | None,
    baseline: dict[str, Any] | None = None,
) -> None:
    lines: list[str] = []
    rs = retrieval["summary"]
    lines.append("# 检索与引用评测报告\n")
    lines.append(
        f"- 用例：`docs/eval/golden_set.jsonl`，共 **{rs['cases']}** 条"
        "（标注到「文档 + 小节」，例如 `01-员工手册.md · 3.1 年假`）"
    )
    if rs["rerank"]:
        lines.append(
            f"- 检索链路：Milvus 混合检索（dense + 内置 BM25 + `RRFRanker(k=60)` 粗排 Top-{settings.rerank_candidate_k}）"
            f" → DashScope `{settings.rerank_model}` Cross-Encoder 精排取 Top-{rs['top_k']}"
        )
    else:
        lines.append(f"- 检索链路：Milvus 服务端混合检索（dense + 内置 BM25 + `RRFRanker(k=60)`），top_k={rs['top_k']}")
    health = knowledge.health()
    lines.append(
        f"- 环境：向量库 backend={health.get('backend')} · collection={health.get('collection')} · "
        f"chunks={health.get('rows')}\n"
    )
    lines.append(f"## 1. 检索指标（{rs['cases']} 条）\n")
    lines.append("| 指标 | 数值 | 含义 |")
    lines.append("|---|---|---|")
    lines.append(f"| Recall@1 | **{rs['recall@1']:.2%}** | 期望小节排第一的比例 |")
    lines.append(f"| Recall@{rs['top_k']} | **{rs['recall@k']:.2%}** | 期望小节进前 {rs['top_k']} 的比例 |")
    lines.append(f"| MRR@{rs['top_k']} | **{rs['mrr@k']:.4f}** | 期望小节排名倒数的平均值（越接近 1 越好） |")
    lines.append(f"| 首条关键词命中率 | {rs['top1_keyword_rate']:.2%} | 首条检索结果里出现期望关键词 |")
    lines.append(f"| 检索延迟 | 平均 {rs['latency_ms_avg']} ms / P95 {rs['latency_ms_p95']} ms | 单次检索全链路 |")
    lines.append("")

    if baseline is not None:
        bs = baseline["summary"]
        d_r1 = (rs["recall@1"] - bs["recall@1"]) * 100
        d_rk = (rs["recall@k"] - bs["recall@k"]) * 100
        d_mrr = rs["mrr@k"] - bs["mrr@k"]
        lines.append("## 2. 消融对照：纯 RRF 粗排 vs RRF + Cross-Encoder 精排\n")
        lines.append(
            f"| 方案 | Recall@1 | Recall@{rs['top_k']} | MRR@{rs['top_k']} | 首条关键词命中 | 平均 / P95 延迟 |"
        )
        lines.append("|---|---|---|---|---|---|")
        lines.append(
            f"| Dense + BM25 + RRF (Top-{rs['top_k']}) | {bs['recall@1']:.2%} | {bs['recall@k']:.2%} | "
            f"{bs['mrr@k']:.4f} | {bs['top1_keyword_rate']:.2%} | {bs['latency_ms_avg']} / {bs['latency_ms_p95']} ms |"
        )
        lines.append(
            f"| **+ `{settings.rerank_model}` 精排 (Top-{settings.rerank_candidate_k} → Top-{rs['top_k']})** | "
            f"**{rs['recall@1']:.2%}** ({d_r1:+.2f}pp) | **{rs['recall@k']:.2%}** ({d_rk:+.2f}pp) | "
            f"**{rs['mrr@k']:.4f}** ({d_mrr:+.4f}) | **{rs['top1_keyword_rate']:.2%}** | "
            f"{rs['latency_ms_avg']} / {rs['latency_ms_p95']} ms |"
        )
        lines.append("")

        # 列出精排改善的典型样本
        base_by_id = {r["id"]: r for r in baseline["rows"]}
        improved = []
        for row in retrieval["rows"]:
            b_row = base_by_id.get(row["id"])
            if not b_row:
                continue
            b_rank = b_row["rank"]
            r_rank = row["rank"]
            if r_rank is not None and (b_rank is None or r_rank < b_rank):
                improved.append((row["id"], row["query"], row["expected"], b_rank, r_rank))
        if improved:
            lines.append("### 精排纠偏的典型样本\n")
            lines.append("| id | 问句 | 期望小节 | RRF 排名 | +精排后排名 |")
            lines.append("|---|---|---|---|---|")
            for cid, q, exp, b_rank, r_rank in improved:
                b_str = f"未进 Top-{rs['top_k']}" if b_rank is None else f"#{b_rank}"
                lines.append(f"| {cid} | {q} | {exp} | {b_str} | **#{r_rank}** |")
            lines.append("")

    sec_no = 3 if baseline is not None else 2
    if answers:
        an = answers["summary"]
        lines.append(f"## {sec_no}. 端到端回答（前 {an['answer_cases']} 条，真模型）\n")
        lines.append("| 指标 | 数值 | 含义 |")
        lines.append("|---|---|---|")
        lines.append(f"| 引用准确率 | **{an['citation_accuracy']:.2%}** | 引用的资料里含期望小节 |")
        lines.append(f"| 引用标记率 | {an['citation_mark_rate']:.2%} | 回答正文带 `[1]` 这类标注 |")
        lines.append(f"| 关键词落进回答 | {an['keyword_in_reply_rate']:.2%} | 回答正文出现期望关键词 |")
        lines.append(f"| 端到端延迟 | 平均 {an['elapsed_s_avg']} s / P95 {an['elapsed_s_p95']} s | 分类 + 检索精排 + 生成 |")
        lines.append(f"| 失败条数 | {an['answer_errors']} | 抛异常的用例 |")
        lines.append("")
        sec_no += 1
        lines.append(f"## {sec_no}. 端到端逐条\n")
        lines.append("| id | 问句 | 期望 | 引用到的 | 引用命中 | 耗时(s) |")
        lines.append("|---|---|---|---|---|---|")
        for row in answers["rows"]:
            if "error" in row:
                lines.append(f"| {row['id']} | {row['query']} | - | 失败：{row['error'][:40]} | ✗ | - |")
                continue
            cited = "、".join(row["cited"]) or "（无引用）"
            lines.append(
                f"| {row['id']} | {row['query']} | {row['expected']} | {cited} | "
                f"{'✓' if row['citation_ok'] else '✗'} | {row['elapsed_s']} |"
            )
        lines.append("")
        sec_no += 1

    lines.append(f"## {sec_no}. 未命中的用例（用于调参）\n")
    misses = [r for r in retrieval["rows"] if not r["hitk"]]
    if not misses:
        lines.append(f"无：全部 **{rs['cases']}** 条用例均已将期望小节排进前 {rs['top_k']}。\n")
    else:
        lines.append("| id | 问句 | 期望 | 实际返回 |")
        lines.append("|---|---|---|---|")
        for row in misses:
            lines.append(f"| {row['id']} | {row['query']} | {row['expected']} | {'、'.join(row['got']) or '空'} |")
        lines.append("")
    sec_no += 1

    lines.append(f"## {sec_no}. 怎么复现\n")
    lines.append("```bash")
    lines.append("cd deploy && docker compose up -d                      # 起 PG / Milvus / attu")
    lines.append(".venv/Scripts/python.exe -m scripts.ingest_docs --md docs/kb/md --to-milvus")
    lines.append(".venv/Scripts/python.exe -m scripts.eval_rag --compare # 跑纯 RRF vs RRF+精排 A/B 对照")
    lines.append(".venv/Scripts/python.exe -m scripts.eval_rag --compare --answers 20  # 加端到端引用指标")
    lines.append("```")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 检索/引用评测")
    parser.add_argument("--top-k", type=int, default=3, help="检索条数（默认 3）")
    parser.add_argument("--answers", type=int, default=0, help="额外跑多少条完整链路（默认 0）")
    parser.add_argument("--no-rerank", action="store_true", help="强制关闭 Cross-Encoder 精排，仅评纯 RRF")
    parser.add_argument("--compare", action="store_true", help="同时跑纯 RRF 与 RRF+精排，输出消融对照表")
    args = parser.parse_args()

    cases = load_cases()
    top_k = max(1, args.top_k)

    baseline: dict[str, Any] | None = None
    if args.compare:
        baseline = evaluate_retrieval(cases, top_k, rerank=False)
        retrieval = evaluate_retrieval(cases, top_k, rerank=True)
    elif args.no_rerank:
        retrieval = evaluate_retrieval(cases, top_k, rerank=False)
    else:
        retrieval = evaluate_retrieval(cases, top_k, rerank=None)

    answers = evaluate_answers(cases, args.answers) if args.answers > 0 else None
    write_report(retrieval, answers, baseline=baseline)

    payload: dict[str, Any] = {"retrieval": retrieval["summary"]}
    if baseline is not None:
        payload["baseline_rrf"] = baseline["summary"]
    if answers:
        payload["answers"] = answers["summary"]
    print(json.dumps(payload, ensure_ascii=False))
    print(f"report -> {REPORT}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
