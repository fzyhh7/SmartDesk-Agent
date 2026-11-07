"""ticket-server：工单域的 MCP 服务（7 个工具：3 读 + 4 写）。

协议与传输：
- Server 用 FastMCP 编写，@ticket_mcp.tool() 暴露工具，ticket_mcp.run(transport="stdio") 独立进程运行
- 工具返回**纯文本 JSON**，客户端解析后写回 State
- stdio 模式下 server 里禁止 print，否则会污染协议流

鉴权（放在 server 里而不是 Agent 里，零信任原则）：
- 每个工具都要求 `actor`（身份票据），tenant_id / reporter 一律用它覆盖，不信模型填的值
- employee 只能读/改/关**自己提的单**；approver 能处理本租户所有单；跨租户一律拒
- 建单去重也在服务端做：同租户同提单人同标题的未关闭单，直接返回原单（deduplicated）

工具清单（10 个工具里的 8 个）：
- query_ticket(actor, ticket_no)                          读
- list_tickets(actor, status, limit)                      读
- create_ticket(actor, title, description, ...)           写，可撤销 → 确认门
- update_ticket(actor, ticket_no, patch)                  写，可撤销 → 确认门
- close_ticket(actor, ticket_no, resolution, notify_reporter) 写，notify 时升级审批
- save_approval(actor, op, target, status, ...)          写，审批留痕（进闸门 pending / 人点了补最终态）
- list_approvals(actor, status, limit)                    读，审批中心的数据源

为什么审批放服务端：
- 审批状态机是"业务事实"，不能只活在 checkpoint blob 里（换掉 Agent 就查不到了）；
- 审批中心要按 tenant/status 分页查，只能在库上查。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.mcp.servers import guard  # noqa: E402

DEFAULT_DB = ROOT_DIR / ".data" / "tickets.sqlite"

ticket_mcp = FastMCP(
    "smartdesk-ticket",
    instructions="企业服务台工单服务：查询、列单、建单、改单、关单。写操作参数由调用方确认后再提交；权限由服务端按 actor 判定。",
)

DDL = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_no   TEXT UNIQUE NOT NULL,
    tenant_id   TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    urgency     TEXT DEFAULT 'medium',
    category    TEXT DEFAULT '其他',
    reporter    TEXT DEFAULT 'agent',
    status      TEXT DEFAULT 'open',
    resolution  TEXT DEFAULT '',
    source      TEXT DEFAULT 'mcp',
    notified    INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_tenant ON tickets(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_tickets_no ON tickets(ticket_no);

CREATE TABLE IF NOT EXISTS approvals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL,
    op          TEXT NOT NULL,
    target      TEXT NOT NULL,
    risk        TEXT DEFAULT 'read',
    summary     TEXT DEFAULT '',
    requester   TEXT DEFAULT '',
    status      TEXT DEFAULT 'pending',
    approver    TEXT DEFAULT '',
    note        TEXT DEFAULT '',
    thread_id   TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    decided_at  TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_approvals_tenant ON approvals(tenant_id, status);
"""

# 老库补列（CREATE TABLE IF NOT EXISTS 不会给已存在的表加字段）：
# 加 thread_id 之前建过的 approvals 表在这里一次性补齐，避免用户手动删库。
APPROVAL_MIGRATIONS = [
    ("thread_id", "ALTER TABLE approvals ADD COLUMN thread_id TEXT DEFAULT ''"),
]

VALID_STATUS = {"open", "in_progress", "closed"}
OPEN_STATUSES = ("open", "in_progress")
APPROVAL_STATUSES = {"pending", "approved", "edited", "rejected"}

def _db_path() -> Path:
    import os

    return Path(os.environ.get("TICKET_DB_PATH") or DEFAULT_DB)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.executescript(DDL)
        _migrate(conn)
        conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """给老库补新增列（幂等：列已存在就跳过）。"""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(approvals)").fetchall()}
    for column, ddl in APPROVAL_MIGRATIONS:
        if column not in columns:
            conn.execute(ddl)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_ticket_no(conn: sqlite3.Connection) -> str:
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"TK-{day}-"
    row = conn.execute(
        "SELECT ticket_no FROM tickets WHERE ticket_no LIKE ? ORDER BY ticket_no DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    seq = 1
    if row:
        try:
            seq = int(str(row["ticket_no"]).split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["notified"] = bool(data.get("notified"))
    return data


def _fetch(conn: sqlite3.Connection, ticket_no: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM tickets WHERE ticket_no = ?", (ticket_no or "",)).fetchone()
    return _row_to_dict(row) if row else None


def _deny_forbidden(actor: dict[str, Any], ticket_no: str) -> str:
    return guard.deny(
        "forbidden",
        f"你没有权限操作工单 {ticket_no}：只有提单人本人或有权限的同事（approver）才能处理",
        actor={"user_id": actor["user_id"], "roles": list(actor["roles"])},
    )


@ticket_mcp.tool()
def create_ticket(
    actor: dict[str, Any],
    title: str,
    description: str = "",
    urgency: str = "medium",
    category: str = "其他",
) -> str:
    """建一张工单（可撤销动作，调用前应经过提单人确认）。租户与提单人取自 actor。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    title = (title or "").strip()
    if not title:
        return guard.deny("invalid_argument", "title 不能为空")
    if urgency not in {"low", "medium", "high"}:
        urgency = "medium"

    _init_db()
    with _connect() as conn:
        # 服务端去重：同租户 + 同提单人 + 同标题的未关闭单，不再重复开
        existing = conn.execute(
            """SELECT * FROM tickets
               WHERE tenant_id = ? AND reporter = ? AND title = ?
                 AND status IN (?, ?)
               ORDER BY id DESC LIMIT 1""",
            (actor_data["tenant_id"], actor_data["user_id"], title, *OPEN_STATUSES),
        ).fetchone()
        if existing:
            return json.dumps(
                {"ok": True, "deduplicated": True, "ticket": _row_to_dict(existing)},
                ensure_ascii=False,
            )

        for _ in range(5):
            ticket_no = _next_ticket_no(conn)
            try:
                conn.execute(
                    """INSERT INTO tickets
                       (ticket_no, tenant_id, title, description, urgency, category,
                        reporter, status, source, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (ticket_no, actor_data["tenant_id"], title, description, urgency, category,
                     actor_data["user_id"], "open", "mcp", _now(), _now()),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            return guard.deny("conflict", "生成工单号失败，请重试")
        row = _fetch(conn, ticket_no)

    return json.dumps({"ok": True, "ticket": row}, ensure_ascii=False)


@ticket_mcp.tool()
def query_ticket(actor: dict[str, Any], ticket_no: str) -> str:
    """按工单号查一张工单（只读）。只能查自己的单；approver 可查本租户任意单。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    _init_db()
    with _connect() as conn:
        ticket = _fetch(conn, ticket_no)
    if not ticket:
        return guard.deny("not_found", f"工单 {ticket_no} 不存在")
    if not guard.can_read_ticket(actor_data, ticket):
        return _deny_forbidden(actor_data, ticket_no)
    ticket.update(guard.ticket_flags(actor_data, ticket))
    return json.dumps({"ok": True, "ticket": ticket}, ensure_ascii=False)


@ticket_mcp.tool()
def list_tickets(actor: dict[str, Any], status: str = "", limit: int = 5) -> str:
    """列工单（只读）。employee 只列自己报的；approver 列本租户全部。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    _init_db()
    sql = "SELECT * FROM tickets WHERE tenant_id = ?"
    params: list[Any] = [actor_data["tenant_id"]]
    if not guard.is_privileged(actor_data):
        sql += " AND reporter = ?"
        params.append(actor_data["user_id"])
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit or 5), 50)))
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    tickets = []
    for row in rows:
        ticket = _row_to_dict(row)
        ticket.update(guard.ticket_flags(actor_data, ticket))
        tickets.append(ticket)
    return json.dumps({"ok": True, "count": len(tickets), "tickets": tickets}, ensure_ascii=False)


@ticket_mcp.tool()
def update_ticket(actor: dict[str, Any], ticket_no: str, patch: dict[str, Any]) -> str:
    """改工单字段（可撤销动作）。patch 支持 status/urgency/title/description/category。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    allowed = {"status", "urgency", "title", "description", "category"}
    patch = {key: value for key, value in (patch or {}).items() if key in allowed}
    if not patch:
        return guard.deny("invalid_argument", "没有可更新的字段")
    if "status" in patch and patch["status"] not in VALID_STATUS:
        return guard.deny("invalid_argument", f"status 只能是 {sorted(VALID_STATUS)}")
    if "urgency" in patch and patch["urgency"] not in {"low", "medium", "high"}:
        return guard.deny("invalid_argument", "urgency 只能是 low/medium/high")

    _init_db()
    with _connect() as conn:
        ticket = _fetch(conn, ticket_no)
        if not ticket:
            return guard.deny("not_found", f"工单 {ticket_no} 不存在")
        if not guard.can_write_ticket(actor_data, ticket):
            return _deny_forbidden(actor_data, ticket_no)
        patch["updated_at"] = _now()
        columns = ", ".join(f"{key} = ?" for key in patch)
        values = list(patch.values()) + [ticket_no]
        conn.execute(f"UPDATE tickets SET {columns} WHERE ticket_no = ?", values)
        row = _fetch(conn, ticket_no)

    return json.dumps(
        {
            "ok": True,
            "ticket": row,
            "updated": "、".join(k for k in patch if k != "updated_at"),
        },
        ensure_ascii=False,
    )


@ticket_mcp.tool()
def close_ticket(
    actor: dict[str, Any],
    ticket_no: str,
    resolution: str = "",
    notify_reporter: bool = False,
) -> str:
    """关单（可撤销动作）。notify_reporter=True 会通知提单人，属对外可见动作，需要主管审批。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    _init_db()
    with _connect() as conn:
        ticket = _fetch(conn, ticket_no)
        if not ticket:
            return guard.deny("not_found", f"工单 {ticket_no} 不存在")
        if not guard.can_write_ticket(actor_data, ticket):
            return _deny_forbidden(actor_data, ticket_no)
        if ticket["status"] == "closed":
            return json.dumps({"ok": True, "ticket": ticket, "already_closed": True}, ensure_ascii=False)
        conn.execute(
            "UPDATE tickets SET status = ?, resolution = ?, notified = ?, updated_at = ? WHERE ticket_no = ?",
            ("closed", resolution or "已解决", 1 if notify_reporter else 0, _now(), ticket_no),
        )
        row = _fetch(conn, ticket_no)

    return json.dumps({"ok": True, "ticket": row}, ensure_ascii=False)


@ticket_mcp.tool()
def save_approval(
    actor: dict[str, Any],
    op: str,
    target: str,
    risk: str = "read",
    status: str = "pending",
    summary: str = "",
    note: str = "",
    approver: str = "",
    thread_id: str = "",
) -> str:
    """记一条审批留痕（审批中心的数据源）。进闸门写 pending，人点了再补最终状态。

    - 同一 tenant + op + target（+ thread）已有 pending 时直接复用：interrupt 恢复会重放节点，这里必须幂等
    - thread_id 是审批中心"点通过"的必要条件：没有它，主管看到待办也不知道 resume 哪条会话
    - 这是 Agent 侧唯一允许写的"审计"；业务数据仍然只有上面 5 个工具能改
    """
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    op = (op or "").strip()
    target = (target or "").strip()
    thread_id = (thread_id or "").strip()
    if not op or not target:
        return guard.deny("invalid_argument", "op 和 target 不能为空")
    if status not in APPROVAL_STATUSES:
        return guard.deny("invalid_argument", f"status 只能是 {sorted(APPROVAL_STATUSES)}")

    _init_db()
    with _connect() as conn:
        # thread_id 有值时才按它匹配：同一张单被两条会话分别操作，应该各留一条痕
        sql = (
            "SELECT * FROM approvals WHERE tenant_id = ? AND op = ? AND target = ?"
            " AND status = 'pending'"
        )
        params: list[Any] = [actor_data["tenant_id"], op, target]
        if thread_id:
            sql += " AND thread_id = ?"
            params.append(thread_id)
        sql += " ORDER BY id DESC LIMIT 1"
        row = conn.execute(sql, params).fetchone()

        if status == "pending":
            if row:  # 节点重放：复用已存在的待办，不重复插
                return json.dumps(
                    {"ok": True, "existing": True, "approval": dict(row)}, ensure_ascii=False
                )
            cur = conn.execute(
                "INSERT INTO approvals"
                " (tenant_id, op, target, risk, summary, requester, status, thread_id, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (actor_data["tenant_id"], op, target, risk or "read", summary or "",
                 actor_data["user_id"], "pending", thread_id, _now()),
            )
            approval_id = cur.lastrowid
        elif row:
            conn.execute(
                "UPDATE approvals SET status = ?, approver = ?, note = ?, thread_id = ?, decided_at = ?"
                " WHERE id = ?",
                (status, approver or "", note or "", thread_id or row["thread_id"],
                 _now(), row["id"]),
            )
            approval_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO approvals"
                " (tenant_id, op, target, risk, summary, requester, status, approver, note,"
                "  thread_id, created_at, decided_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (actor_data["tenant_id"], op, target, risk or "read", summary or "",
                 actor_data["user_id"], status, approver or "", note or "",
                 thread_id, _now(), _now()),
            )
            approval_id = cur.lastrowid

    return json.dumps({"ok": True, "approval_id": approval_id, "status": status}, ensure_ascii=False)


@ticket_mcp.tool()
def list_approvals(actor: dict[str, Any], status: str = "", limit: int = 20) -> str:
    """审批中心：列审批留痕（只读）。approver 看本租户全部；employee 只看自己申请的。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    sql = "SELECT * FROM approvals WHERE tenant_id = ?"
    params: list[Any] = [actor_data["tenant_id"]]
    if not guard.is_privileged(actor_data):
        sql += " AND requester = ?"
        params.append(actor_data["user_id"])
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit or 20), 100)))
    _init_db()
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        # 自己批自己：不拦，但要标出来（4-eyes 原则在页面上看得见）
        item["self_approved"] = bool(item.get("approver")) and item.get("approver") == item.get("requester")
        items.append(item)
    return json.dumps({"ok": True, "count": len(items), "approvals": items}, ensure_ascii=False)


if __name__ == "__main__":
    ticket_mcp.run(transport="stdio", show_banner=False)