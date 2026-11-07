"""所有 HTTP 接口（一个文件放完）。

这一层很薄，只做三件事：解析请求 → 从请求头组出 `UserContext` → 调图或调工具。
业务逻辑一行都不在这里：权限判定在 MCP server，流程编排在 `agents/graph.py`。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from ..agents.graph import get_graph
from ..agents.nodes.action_spec import fields_of, label_of, summary_of
from ..agents.state import UserContext, initial_state
from ..agents.tools import ticket_tools
from .deps import actor_of_context, get_context
from .schemas import ChatRequest, ResumeRequest
from .streaming import iter_sse

router = APIRouter()

# SSE 必须关掉代理缓冲，否则 token 会被攒着一次性吐出来
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _identity(context: UserContext) -> dict[str, Any]:
    """把身份塞进 meta 事件，前端用来显示"当前是谁在问"。"""
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "roles": list(context.roles),
    }


def _sse(events) -> StreamingResponse:
    return StreamingResponse(events, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat/stream", summary="发一句话，流式返回（token / 节点进度 / 暂停）")
def chat_stream(
    body: ChatRequest, context: UserContext = Depends(get_context)
) -> StreamingResponse:
    """知识型：`token` 逐字输出 → `done`（带引用）；动作型：`node`…→ `interrupt`（卡片）。"""
    graph = get_graph()
    config = {"configurable": {"thread_id": body.thread_id}}

    # 这条 thread 还停在闸门上：再发新消息会把挂起的 checkpoint 冲掉，
    # 之后主管 resume 就查不到 interrupt 了（只能收到 409）。直接拒绝，让前端提示"先处理待办"。
    snapshot = graph.get_state(config)
    if snapshot.values and snapshot.interrupts:
        pending = getattr(snapshot.interrupts[0], "value", None) or {}
        raise HTTPException(
            status_code=409,
            detail=(
                f"会话 {body.thread_id} 正在等待"
                f"{'审批' if pending.get('type') == 'approve' else '确认'}，"
                "请先处理挂起的卡片，或换一个 thread_id 新开会话。"
            ),
        )

    state = initial_state(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        thread_id=body.thread_id,
        query=body.message,
    )
    events = iter_sse(
        graph,
        state,
        config,
        context=context,
        thread_id=body.thread_id,
        identity=_identity(context),
    )
    return _sse(events)


@router.post("/runs/{thread_id}/resume", summary="从暂停点继续（确认 / 审批 / 补参数）")
def resume_run(
    thread_id: str,
    body: ResumeRequest,
    context: UserContext = Depends(get_context),
) -> StreamingResponse:
    """跨进程恢复的关键：只靠 `thread_id` 找回 checkpoint，不需要把 State 传回来。

    谁在 resume 决定"能不能点通过"：审批门会按**这次请求的请求头身份**再判一次权限，
    所以员工自己点通过只会继续挂起，主管用同一个 thread_id 来 resume 才生效。
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"没有这个会话：{thread_id}")
    stored_tenant = snapshot.values.get("tenant_id")
    if stored_tenant and stored_tenant != context.tenant_id:
        raise HTTPException(status_code=403, detail="thread 不属于这个租户")
    if not snapshot.interrupts:
        raise HTTPException(status_code=409, detail="这个会话没有停在闸门上，不需要 resume")

    events = iter_sse(
        graph,
        Command(resume=body.to_resume_payload()),
        config,
        context=context,
        thread_id=thread_id,
        identity=_identity(context),
    )
    return _sse(events)


@router.get("/runs/{thread_id}", summary="会话当前快照（停在哪、状态、草稿卡片）")
def read_run(thread_id: str, context: UserContext = Depends(get_context)) -> dict[str, Any]:
    """页面刷新后靠这个接口把"审批卡片"重新画出来。"""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"没有这个会话：{thread_id}")

    values = dict(snapshot.values or {})
    if values.get("tenant_id") and values["tenant_id"] != context.tenant_id:
        raise HTTPException(status_code=403, detail="thread 不属于这个租户")

    interrupts = [getattr(item, "value", None) for item in (snapshot.interrupts or ())]
    action = values.get("action") or {}
    return {
        "thread_id": thread_id,
        "next": list(snapshot.next or ()),
        "paused": bool(interrupts),
        "interrupt": interrupts[0] if interrupts else None,
        "outcome": values.get("outcome"),
        "intent": values.get("intent"),
        "gate": values.get("gate"),
        "risk": values.get("risk"),
        "query": values.get("query"),
        "reply": values.get("reply"),
        "citations": [
            hit.get("citation") or hit.get("title") for hit in (values.get("policy_evidence") or [])
        ],
        "view": {
            "op": action.get("op"),
            "label": label_of(action),
            "summary": summary_of(action),
            "fields": fields_of(action),
            "risk": values.get("risk"),
        }
        if action
        else None,
        "approval": values.get("approval"),
        "ticket_no": _ticket_no(values.get("result")),
        "via": values.get("via"),
    }


def _ticket_no(result: dict[str, Any] | None) -> str | None:
    """单号从工具返回值现取，State 里不再存第二份。"""
    data = result or {}
    ticket = data.get("ticket") if isinstance(data.get("ticket"), dict) else {}
    return ticket.get("ticket_no") or data.get("ticket_no") or None


@router.get("/graph/mermaid", summary="主图 Mermaid（和 CLI 的 graph 子命令同源）")
def graph_mermaid() -> dict[str, str]:
    return {"mermaid": get_graph().get_graph().draw_mermaid()}


@router.get("/tickets", summary="工单列表（员工只看自己报的；主管看全租户）")
def list_tickets(
    status: str = Query(default="", description="open / in_progress / closed"),
    limit: int = Query(default=20, ge=1, le=50),
    context: UserContext = Depends(get_context),
) -> dict[str, Any]:
    """权限在 MCP server 里判（`list_tickets` 内部按 actor 过滤），这里不重复实现。"""
    return ticket_tools.list_tickets(actor_of_context(context), status=status, limit=limit)


@router.get("/approvals", summary="审批中心（谁申请、什么事、批没批）")
def list_approvals(
    status: str = Query(default="", description="pending / approved / edited / rejected"),
    limit: int = Query(default=20, ge=1, le=100),
    context: UserContext = Depends(get_context),
) -> dict[str, Any]:
    """权限同样在 server 侧：非特权角色只能看到自己发起的审批。"""
    return ticket_tools.list_approvals(actor_of_context(context), status=status, limit=limit)
