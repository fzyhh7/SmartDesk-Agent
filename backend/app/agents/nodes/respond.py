"""respond 节点：把结构化结果组织成"员工看得懂的一段话"，交给 FastAPI/前端。

核心职责：
- 流式输出或中断恢复的最后一步，将 State 中的结构化字段拼成最终回复文本
- 回复里要带可执行的"下一步"指引，而不是只回一个 ok

按链路分三种：
- 闲聊：交给模型自由对话（`CHAT_SYSTEM_PROMPT`），**不检索知识库**，也不碰任何写操作
- 知识：answer 节点已经写好了带引用的回答（这里直接透传）
- 动作：按 result 说清楚"办成了没有、单号是多少、走了哪条通道、被谁确认/审批"

注意：只有闲聊分支会调模型；知识与动作分支都是纯模板（数据已在前面节点算好）。
"""

from __future__ import annotations

import logging
from typing import Any

from ..llm import get_chat_model
from ..prompts.service_desk import CHAT_SYSTEM_PROMPT
from ..state import TicketState

logger = logging.getLogger(__name__)


def _chat_reply(state: TicketState) -> str:
    """闲聊：直接让模型对话，不检索知识库（避免寒暄也走一遍 Milvus）。

    模型挂了就退回一句固定能力说明——闲聊降级不影响主流程。
    """
    query = str(state.get("query") or "").strip()
    fallback = (
        "你好，我是企业服务台助手。你可以直接问我制度流程（例如「发票怎么开」「年假多少天」），"
        "也可以让我办事（例如「帮我建个工单：财务系统登录不上」「把 TK-20261031-0001 关掉」）。"
    )
    if not query:
        return fallback
    try:
        message = get_chat_model().invoke(
            [("system", CHAT_SYSTEM_PROMPT), ("user", query)]
        )
    except Exception:  # noqa: BLE001 - 闲聊失败不该让整条链路 500
        logger.warning("闲聊模型调用失败，退回固定话术", exc_info=True)
        return fallback
    text = getattr(message, "content", "")
    if isinstance(text, list):
        text = "".join(
            str(block.get("text") or "") if isinstance(block, dict) else str(block)
            for block in text
        )
    return str(text).strip() or fallback


def _action_reply(state: TicketState) -> str:
    action = state.get("action") or {}
    result = state.get("result") or {}
    label = action.get("label") or "操作"
    op = action.get("op") or ""
    args = action.get("args") or {}

    existing = (state.get("reply") or "").strip()
    if state.get("outcome"):
        return existing or f"{label}没有执行。需要的话换个说法再来一次。"

    if not result:
        return f"{label}已完成。"

    if not result.get("ok"):
        error = result.get("error") or "未知错误"
        if isinstance(error, dict):
            # server 侧鉴权/校验失败时回的是 {"code":..,"reason":..}，只把 reason 说给员工听
            error = error.get("reason") or error.get("code") or "未知错误"
        return (
            f"{label}没成功：{error}\n"
            "已经把失败原因记录下来，你可以稍后重试，或找受理人看一眼日志。"
        )

    if op == "create_ticket":
        ticket = result.get("ticket") or {}
        ticket_no = ticket.get("ticket_no") or result.get("ticket_no") or "（未返回单号）"
        if result.get("deduplicated"):
            return (
                f"这条和你之前提的是同一件事，我直接复用了原来的工单 {ticket_no}"
                f"（状态：{ticket.get('status', 'open')}），没有重复建单。"
            )
        lines = [
            f"已建单：{ticket_no}",
            f"标题：{ticket.get('title') or args.get('title')}",
            f"优先级：{ticket.get('urgency') or args.get('urgency')}",
            f"状态：{ticket.get('status', 'open')}（提单人：{ticket.get('reporter', '-')}）",
        ]
        lines += [
            "",
            f"通道：MCP · {result.get('server', 'ticket')}-server",
            "处理人会在工单里回复进展；你也可以随时问我「查一下 " + str(ticket_no) + "」。",
        ]
        return "\n".join(lines)

    if op == "close_ticket":
        ticket = result.get("ticket") or {}
        ticket_no = ticket.get("ticket_no") or args.get("ticket_no") or ""
        notify = "，并已通知提单人" if args.get("notify_reporter") else ""
        return f"已关闭工单 {ticket_no}{notify}。如果问题复现，随时告诉我再开一张。"

    if op == "update_ticket":
        ticket = result.get("ticket") or {}
        return f"已更新工单 {ticket.get('ticket_no') or args.get('ticket_no')}：{result.get('updated') or '字段已改'}。"

    if op == "publish_kb_article":
        doc_id = result.get("doc_id") or "-"
        approval = state.get("approval") or {}
        who = approval.get("approver") or "知识库 owner"
        return (
            f"已发布知识文章（{doc_id}），审批人：{who}。\n"
            "现在全员都能在知识库里搜到这篇，后续同类问题会直接引用它。"
        )

    if op == "query_ticket":
        ticket = result.get("ticket") or {}
        return (
            f"工单 {ticket.get('ticket_no')}：{ticket.get('title')}\n"
            f"状态：{ticket.get('status')}｜优先级：{ticket.get('urgency')}｜提单人：{ticket.get('reporter')}"
        )

    if op == "list_tickets":
        tickets = result.get("tickets") or []
        if not tickets:
            return "这个租户下暂时没有工单。"
        lines = [f"最近 {len(tickets)} 张工单："]
        for ticket in tickets:
            lines.append(
                f"- {ticket.get('ticket_no')}｜{ticket.get('status')}｜{ticket.get('urgency')}｜{ticket.get('title')}"
            )
        return "\n".join(lines)

    return f"{label}已完成。"


def compose_reply(state: TicketState) -> dict[str, Any]:
    intent = state.get("intent") or "knowledge"
    reply = state.get("reply")

    if intent == "chat":
        reply = _chat_reply(state)
    elif intent == "action":
        reply = _action_reply(state)
    elif not reply:
        reply = "我没能生成回答，请换个说法再问一次。"

    if state.get("outcome") == "failed" and not reply:
        reply = "这次没有执行成功，请稍后再试或换一种说法。"

    return {"reply": reply}