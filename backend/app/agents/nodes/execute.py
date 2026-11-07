"""execute 节点：全图唯一允许"真正改数据"的地方。

设计要点：
- 把所有写库动作集中到单一节点，便于统一做审计兜底、异常捕获与幂等识别
- 工具不在 Agent 进程内直接改库，统一通过 MCP 协议调用（FastMCP server + MultiServerMCPClient）
- 业务中断（确认/审批）已在前置闸门完成，本节点额外做最后一道不可逆动作审批凭证复核，且工具服务端还会按 actor 再做一次权限校验

这里做四件事：
1. 装身份：从 Runtime Context 取 actor（工单 / 知识库 server 都按它再判一次权限）
2. 调工具：按 action.server / action.op 分派到对应 MCP server，只传该工具允许的参数
3. 记结果：result / ticket_no / via 写回 State（后续 compose_reply 用它组织话术）
4. 兜底：工具挂了不让整条链路崩，返回结构化错误

注意：**去重（幂等）已经在 ticket_server 里做完了**，这里只认它回的 deduplicated 标记。
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.runtime import Runtime

from ..state import TicketState, UserContext, actor_of

logger = logging.getLogger(__name__)


def _call_tool(server: str, op: str, args: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
    """按 server + op 分派到对应的工具封装；参数白名单在这里收口。"""
    if server == "kb":
        from ..tools import kb_tools

        if op == "publish_kb_article":
            return kb_tools.publish_kb_article(
                actor,
                title=args.get("title") or "",
                content=args.get("content") or "",
                tags=args.get("tags") or [],
                change_note=args.get("change_note") or "",
            )
        if op == "search_kb":
            return kb_tools.search_kb(actor, args.get("query") or "", top_k=int(args.get("top_k") or 3))
        return {"ok": False, "error": {"code": "unsupported", "reason": f"kb server 不支持 {op}"}}

    from ..tools import ticket_tools

    if op == "create_ticket":
        return ticket_tools.create_ticket(
            actor,
            title=args.get("title") or "",
            description=args.get("description") or "",
            urgency=args.get("urgency") or "medium",
            category=args.get("category") or "其他",
        )
    if op == "update_ticket":
        return ticket_tools.update_ticket(actor, args.get("ticket_no") or "", args.get("patch") or {})
    if op == "close_ticket":
        return ticket_tools.close_ticket(
            actor,
            args.get("ticket_no") or "",
            resolution=args.get("resolution") or "",
            notify_reporter=bool(args.get("notify_reporter")),
        )
    if op == "query_ticket":
        return ticket_tools.query_ticket(actor, args.get("ticket_no") or "")
    if op == "list_tickets":
        return ticket_tools.list_tickets(
            actor,
            status=args.get("status") or "",
            limit=int(args.get("limit") or 10),
        )
    return {"ok": False, "error": {"code": "unsupported", "reason": f"ticket server 不支持 {op}"}}


def execute_action(state: TicketState, runtime: Runtime[UserContext]) -> dict[str, Any]:
    action = state.get("action") or {}
    op = action.get("op") or ""
    server = action.get("server") or server_of(op)
    args = dict(action.get("args") or {})
    actor = actor_of(runtime)

    # 最后一道闸门复核：不可逆动作必须带着"已批准"的凭证，否则一律不执行。
    # （路由已经保证不会走到这里；这一层防的是以后有人改图/改路由把闸门绕过去）
    approved = bool((state.get("approval") or {}).get("approver"))
    if state.get("risk") == "write_irreversible" and not approved:
        return {
            "result": {"ok": False, "error": {"code": "blocked", "reason": "不可逆动作缺少审批"}, "op": op},
            "outcome": "failed",
            "reply": None,
        }

    try:
        data = _call_tool(server, op, args, actor)
    except Exception as exc:
        logger.exception("execute 调用 %s.%s 失败", server, op)
        return {
            "result": {"ok": False, "error": {"code": "tool_error", "reason": str(exc)}, "op": op},
            "outcome": "failed",
            "reply": None,
        }

    ok = bool(data.get("ok"))
    deduplicated = bool(data.get("deduplicated"))
    result = {**data, "op": op, "server": server}

    if ok:
        via = "mcp_dedup" if deduplicated else "mcp_ok"
    elif (data.get("error") or {}).get("code") == "forbidden" if isinstance(data.get("error"), dict) else False:
        via = "mcp_denied"
    else:
        via = "mcp_failed"

    return {
        "result": result,
        "via": via,
        "outcome": None if ok else "failed",
        "reply": None,
    }