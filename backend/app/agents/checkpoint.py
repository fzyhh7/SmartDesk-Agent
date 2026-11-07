"""Checkpointer：让中断（interrupt）真正"落盘"，进程重启还能恢复。

设计要点：
- 支持 PostgresSaver（生产持久化）与 SqliteSaver（本地无 PG 环境兜底）
- 编译主图时注入 compile(checkpointer=...)，所有运行态与中断点按 thread_id 串联
- PostgresSaver 优先，连不上就自动回退 SqliteSaver（打印一行警告）。
  两者对外接口完全一致，graph.py 一行都不用改 —— 这就是 checkpointer 抽象的价值。
"""

from __future__ import annotations

import fnmatch
import sqlite3
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from .settings import ensure_data_dir, settings

_bundle: dict[str, Any] = {"saver": None, "conn": None, "backend": ""}


def _init_postgres() -> None:
    """连接 PG 并建表（checkpoints / checkpoint_blobs / checkpoint_writes / migrations）。

    关键点（踩坑记录）：
    - 必须 autocommit=True，否则 PostgresSaver 的建表/写入会在事务里挂住；
    - prepare_threshold=0 关闭 psycopg 的 prepared statement 缓存，
      避免 checkpoint 频繁 DDL/长连接下出现 "prepared statement already exists"；
    - row_factory=dict_row 让返回行是 dict（PostgresSaver 内部按下标取值也能用，
      但官方 from_conn_string 就是这么设的，保持一致）。
    """
    import psycopg
    from psycopg.rows import dict_row

    from langgraph.checkpoint.postgres import PostgresSaver

    conn = psycopg.connect(
        settings.database_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        connect_timeout=5,
    )
    saver = PostgresSaver(conn)
    saver.setup()
    _bundle.update(saver=saver, conn=conn, backend="postgres")


def _init_sqlite() -> None:
    from langgraph.checkpoint.sqlite import SqliteSaver

    ensure_data_dir()
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    _bundle.update(saver=saver, conn=conn, backend="sqlite")


def get_checkpointer() -> BaseCheckpointSaver:
    """懒加载单例：同一进程共用一个连接。"""
    if _bundle["saver"] is not None:
        return _bundle["saver"]

    if settings.checkpoint_backend == "postgres":
        try:
            _init_postgres()
        except Exception as exc:  # noqa: BLE001 - 演示项目：连不上就降级
            print(
                f"[checkpoint] Postgres 不可用（{type(exc).__name__}: {exc}），"
                f"回退 SQLite: {settings.db_path}",
                flush=True,
            )
    if _bundle["saver"] is None:
        _init_sqlite()
    return _bundle["saver"]


def checkpoint_backend_in_use() -> str:
    """给 CLI / 健康检查显示当前真实生效的后端。"""
    get_checkpointer()
    return _bundle["backend"]


def close_checkpointer() -> None:
    conn = _bundle.get("conn")
    if conn is not None:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass
    _bundle.update(saver=None, conn=None, backend="")


def thread_config(thread_id: str) -> dict[str, Any]:
    """所有 invoke / 恢复 / 查状态都靠这个 thread_id 串起来。"""
    return {"configurable": {"thread_id": thread_id}}


# ---------------------------------------------------------------------------
# 线程枚举与删除：只给 CLI 用（scripts/reset_demo.py、排查脚本），主图不碰。
# 之所以不用 saver.list()：PostgresSaver.list() 的签名在不同版本里改过，
# 而 "有哪些 thread_id" 这件事一张 SQL 就能问清，两种后端写法只差一个 fetch。
# ---------------------------------------------------------------------------
def checkpoint_stats() -> dict[str, Any]:
    """返回 {"backend": "postgres"|"sqlite", "threads": [...]}。"""
    get_checkpointer()
    conn = _bundle["conn"]
    if _bundle["backend"] == "postgres":
        with conn.cursor() as cur:  # type: ignore[union-attr]
            cur.execute("select distinct thread_id from checkpoints order by 1")
            rows = cur.fetchall()
        threads = [str(r["thread_id"]) for r in rows]
    else:
        rows = conn.execute(  # type: ignore[union-attr]
            "select distinct thread_id from checkpoints order by 1"
        ).fetchall()
        threads = [str(r[0]) for r in rows]
    return {"backend": _bundle["backend"], "threads": threads}


def delete_threads(patterns: list[str] | None = None) -> list[str]:
    """按 glob 删除 checkpoint 线程，返回真正删掉的 thread_id 列表。

    只删 checkpoint（会话运行态），不动工单和审批记录 —— 那两样在 ticket-server 的
    SQLite 里，是有业务含义的事实，删不删由调用方另外决定。
    """
    saver = get_checkpointer()
    wanted = patterns or ["*"]
    targets = [
        tid
        for tid in checkpoint_stats()["threads"]
        if any(fnmatch.fnmatch(tid, pat) for pat in wanted)
    ]
    for tid in targets:
        saver.delete_thread(tid)
    return targets