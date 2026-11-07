"""工单工具（工单 server 的语义封装）。

节点里只认这些函数名；真正的实现在 `backend/app/mcp/servers/ticket_server.py` 的 8 个 @mcp.tool。
这里不做业务判断，只做「塞身份票据 actor + 参数整理 + 调用 + 返回 dict」。
`actor` 必须由节点从 Runtime Context 构造，**不许从模型输出里取**（否则等于没鉴权）。
"""

from __future__ import annotations

from typing import Any

from .mcp_client import call_tool

SERVER = "ticket"


def create_ticket(
    actor: dict[str, Any],
    *,
    title: str,
    description: str = "",
    urgency: str = "medium",
    category: str = "其他",
) -> dict[str, Any]:
    return call_tool(
        SERVER,
        "create_ticket",
        {"actor": actor, "title": title, "description": description, "urgency": urgency, "category": category},
    )


def query_ticket(actor: dict[str, Any], ticket_no: str) -> dict[str, Any]:
    return call_tool(SERVER, "query_ticket", {"actor": actor, "ticket_no": ticket_no})


def list_tickets(actor: dict[str, Any], *, status: str = "", limit: int = 5) -> dict[str, Any]:
    return call_tool(SERVER, "list_tickets", {"actor": actor, "status": status, "limit": limit})


def update_ticket(actor: dict[str, Any], ticket_no: str, patch: dict[str, Any]) -> dict[str, Any]:
    return call_tool(SERVER, "update_ticket", {"actor": actor, "ticket_no": ticket_no, "patch": patch})


def close_ticket(
    actor: dict[str, Any],
    ticket_no: str,
    *,
    resolution: str = "",
    notify_reporter: bool = False,
) -> dict[str, Any]:
    return call_tool(
        SERVER,
        "close_ticket",
        {"actor": actor, "ticket_no": ticket_no, "resolution": resolution, "notify_reporter": notify_reporter},
    )


def save_approval(
    actor: dict[str, Any],
    *,
    op: str,
    target: str,
    risk: str = "read",
    status: str = "pending",
    summary: str = "",
    note: str = "",
    approver: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    """审批留痕：进闸门写 pending，人点了写最终状态（幂等，节点重放安全）。

    thread_id 必须带上：审批中心靠它把 pending 记录映射回"哪一条会话"，
    否则主管就算看到待办，也不知道该 resume 哪条 thread。
    """
    return call_tool(
        SERVER,
        "save_approval",
        {
            "actor": actor,
            "op": op,
            "target": target,
            "risk": risk,
            "status": status,
            "summary": summary,
            "note": note,
            "approver": approver,
            "thread_id": thread_id,
        },
    )


def list_approvals(actor: dict[str, Any], *, status: str = "", limit: int = 20) -> dict[str, Any]:
    return call_tool(SERVER, "list_approvals", {"actor": actor, "status": status, "limit": limit})


