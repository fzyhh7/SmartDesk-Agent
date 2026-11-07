"""重置演示数据：清工单/审批、清会话 checkpoint，可选清知识库。

默认是 **dry-run**（只打印"将要删除什么"，一行都不删），必须显式加 --yes 才真执行。
知识库默认不动 —— 重建要重新跑 embedding，而且跟"我说错话了想重来"无关。

用法：
    python -m scripts.reset_demo                            # 预览：清哪些、留哪些
    python -m scripts.reset_demo --yes                      # 真删（工单 + 审批 + 全部会话）
    python -m scripts.reset_demo --yes --threads "web-*"    # 只删网页端产生的会话
    python -m scripts.reset_demo --yes --keep-tickets       # 只清会话，工单审批留着
    python -m scripts.reset_demo --yes --keep-threads       # 只清工单审批，会话留着
    python -m scripts.reset_demo --yes --kb                 # 连 Milvus 知识库一起清（清完要重新灌）

删完之后：
    - 工单/审批：ticket-server 下次调用会自动 _init_db() 重建表结构（含 thread_id 迁移）；
    - 会话：删的是 checkpoint，主图的 State 没了，就不能再 resume 那条 thread（预期行为）；
    - 知识库：collection 被 drop 掉，要用
        python -m scripts.ingest_docs --md docs/kb/md --to-milvus --force
      重新灌一遍。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 这两个 import 放到函数里：--help 时不该去连 Postgres / Milvus
from backend.app.agents.settings import settings  # noqa: E402

BUSINESS_TABLES = ("tickets", "approvals")


def _ticket_db_path() -> Path:
    """和 backend/app/mcp/servers/ticket_server.py 的 _db_path() 保持一致。"""
    override = os.environ.get("TICKET_DB_PATH")
    return Path(override) if override else ROOT / ".data" / "tickets.sqlite"


def _business_counts(path: Path) -> dict[str, int] | None:
    """工单库不存在时返回 None（说明还没跑过任何写操作）。"""
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("select name from sqlite_master where type='table'").fetchall()
        existing = {str(r[0]) for r in rows}
        return {
            name: conn.execute(f"select count(*) from {name}").fetchone()[0]
            for name in BUSINESS_TABLES
            if name in existing
        }
    finally:
        conn.close()


def _wipe_business(path: Path) -> dict[str, int]:
    """按表删行并归零自增序列；表结构留着（相当于"清空"而不是"删库"）。"""
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("select name from sqlite_master where type='table'").fetchall()
        existing = {str(r[0]) for r in rows}
        deleted: dict[str, int] = {}
        for name in BUSINESS_TABLES:
            if name not in existing:
                continue
            deleted[name] = conn.execute(f"select count(*) from {name}").fetchone()[0]
            conn.execute(f"delete from {name}")
        if "sqlite_sequence" in existing:
            marks = ",".join(f"'{name}'" for name in BUSINESS_TABLES)
            conn.execute(f"delete from sqlite_sequence where name in ({marks})")
        conn.commit()
        return deleted
    finally:
        conn.close()


def _kb_rows() -> int | None:
    """Milvus 里现在有多少条 chunk；连不上返回 None（不阻断重置流程）。"""
    try:
        from backend.app.agents.rag import vector_store

        return int(vector_store.collection_stats().get("rows") or 0)
    except Exception as exc:  # noqa: BLE001 - 演示项目：连不上就如实说
        print(f"  （知识库读不到：{type(exc).__name__}: {exc}）")
        return None


def _wipe_kb() -> None:
    from backend.app.agents.rag import vector_store

    vector_store.get_client().drop_collection(settings.milvus_collection)


def _line(label: str, detail: str, action: str) -> None:
    print(f"  {label:<14}{detail:<26}{action}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reset_demo",
        description="重置演示数据（默认 dry-run，加 --yes 才真删）",
    )
    parser.add_argument("--yes", action="store_true", help="真删；不加就是预览")
    parser.add_argument(
        "--threads",
        action="append",
        default=None,
        metavar="PATTERN",
        help='只删匹配的会话，可重复，如 --threads "web-*" --threads "t-*"（默认全部）',
    )
    parser.add_argument("--keep-tickets", action="store_true", help="保留工单与审批记录")
    parser.add_argument("--keep-threads", action="store_true", help="保留会话 checkpoint")
    parser.add_argument("--kb", action="store_true", help="连 Milvus 知识库一起清（清完要重新灌）")
    parser.add_argument(
        "--keep-kb",
        action="store_true",
        help="保留知识库（本来就是默认，写出来只是让意图更明确）",
    )
    args = parser.parse_args()

    if args.kb and args.keep_kb:
        parser.error("--kb 和 --keep-kb 不能同时用")

    patterns = args.threads or ["*"]
    mode = "执行" if args.yes else "预览（dry-run，不删除任何东西）"
    print("=" * 74)
    print(f"SmartDesk 演示数据重置 · {mode}")
    print("=" * 74)

    # ---------- 1. 工单与审批（ticket-server 的 SQLite）----------
    db_path = _ticket_db_path()
    counts = _business_counts(db_path)
    print(f"\n[1] 工单 / 审批　{db_path.relative_to(ROOT) if db_path.is_relative_to(ROOT) else db_path}")
    if counts is None:
        print("  库文件还不存在，没什么可清的。")
    else:
        for name in BUSINESS_TABLES:
            if name not in counts:
                continue
            verb = "保留" if args.keep_tickets else "会删除"
            _line(name, f"{counts[name]} 行", verb)

    # ---------- 2. 会话 checkpoint ----------
    from backend.app.agents.checkpoint import checkpoint_stats, delete_threads

    try:
        stats = checkpoint_stats()
        all_threads = stats["threads"]
    except Exception as exc:  # noqa: BLE001
        print(f"\n[2] 会话 checkpoint：读不到（{type(exc).__name__}: {exc}）")
        stats, all_threads = {"backend": "unknown"}, []

    import fnmatch

    matched = [t for t in all_threads if any(fnmatch.fnmatch(t, p) for p in patterns)]
    print(f"\n[2] 会话 checkpoint　后端 = {stats['backend']}　匹配 {' / '.join(patterns)}")
    if args.keep_threads:
        _line("会话", f"共 {len(all_threads)} 条", "保留")
    else:
        _line("会话", f"匹配 {len(matched)} / 共 {len(all_threads)} 条", "会删除")
        for tid in matched[:10]:
            print(f"      - {tid}")
        if len(matched) > 10:
            print(f"      … 还有 {len(matched) - 10} 条")

    # ---------- 3. 知识库（默认保留）----------
    kb_rows = _kb_rows()
    print(f"\n[3] 知识库　collection = {settings.milvus_collection}")
    _line(
        "chunk",
        "读不到" if kb_rows is None else f"{kb_rows} 条",
        "会 drop" if args.kb else "保留",
    )

    if not args.yes:
        print("\n以上是预览。确认无误后执行：\n")
        tail = " --keep-tickets" if args.keep_tickets else ""
        tail += " --keep-threads" if args.keep_threads else ""
        tail += " --kb" if args.kb else ""
        thread_arg = "" if patterns == ["*"] else " " + " ".join(f'--threads "{p}"' for p in patterns)
        print(f"  python -m scripts.reset_demo --yes{thread_arg}{tail}")
        return 0

    # ---------- 真删 ----------
    print("\n开始执行 …")
    if counts is not None and not args.keep_tickets and counts:
        deleted = _wipe_business(db_path)
        print("  ✓ 工单/审批已清空：" + "，".join(f"{k} {v} 行" for k, v in deleted.items()))
    if not args.keep_threads and matched:
        done = delete_threads(patterns)
        print(f"  ✓ 已删除 {len(done)} 条会话 checkpoint")
    if args.kb:
        _wipe_kb()
        print(
            "  ✓ 已 drop collection "
            f"{settings.milvus_collection}，请重新灌库：\n"
            "      python -m scripts.ingest_docs --md docs/kb/md --to-milvus --force"
        )
    print("\n完成。现在是一个干净的演示状态。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
