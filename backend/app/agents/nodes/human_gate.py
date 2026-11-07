"""三个闸门（clarify / confirm / approve）共用的解析、留痕，以及两个"停人"的闸门。

设计要点：
- 基于 LangGraph `interrupt()` 实现业务级人工介入（把待确认参数、来源标记、制度引用一并交给前端渲染）
- 依托 checkpointer 记住中断位置，支持跨进程按 `thread_id` 恢复
- 审批权限来自只读 `UserContext.roles`，绝不让模型自行判断权限

两个闸门的分工（面试最容易被追问的一点）：
- `confirm_action`（确认门）：**可撤销**动作，由提单人本人看一眼参数 → 可改 → 确认
- `approve_action`（审批门）：**不可逆 / 全员可见**动作，由有权限的人点通过 → 撤不回

三条必须记住的语义：
1. **发起 ≠ 批准**：任何员工都能发起不可逆动作（只进 pending 队列），能不能点通过只看
   恢复那一刻的身份——没权限就继续挂起，绝不替别人点。
2. **确认后要重算风险**：员工可能在确认卡上改出不可逆参数（关单时勾"顺便通知提单人"），
   那就不能直接执行，要补一道审批（风险表仍是唯一来源：RISK_BY_OP）。
3. **恢复会重放节点**：interrupt 恢复时本节点从头再跑一遍，所以留痕必须幂等
   （`record_approval` → server 侧 `save_approval` 对同一 pending 直接复用）。

resume 的载荷允许三种写法，这里统一归一化成 {"type", "patch", "message", "answers"}：
1. {"type": "decision", "decision": {"type": "approve"}}
2. {"decision": "approve"}
3. "approve"
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ..state import TicketState, UserContext, actor_of
from ..tools import ticket_tools
from .action_spec import fields_of, label_of, summary_of
from .plan_action import GATE_BY_RISK, RISK_BY_OP, compute_risk

logger = logging.getLogger(__name__)

VALID_DECISIONS = ("approve", "edit", "reject")

# 闸门结果 → 审批表状态（approved / edited / rejected）
DECISION_STATUS = {"approve": "approved", "edit": "edited", "reject": "rejected"}

# 谁能批：审批权来自 Context.roles（不是模型说了算）
APPROVER_ROLES: dict[str, tuple[tuple[str, ...], str]] = {
    "publish_kb_article": (("kb_owner",), "知识库 owner "),
    "close_ticket": (("approver",), "主管"),
}
DEFAULT_APPROVER = (("approver", "kb_owner"), "有权限的同事 ")


# --------------------------------------------------------------------------- #
# 一、resume 载荷解析与参数合并（两个闸门共用）
# --------------------------------------------------------------------------- #
def normalize_human_input(answer: Any) -> dict[str, Any]:
    """把 interrupt 恢复值整理成 {"type":..., "patch":..., "message":..., "answers":...}。"""
    if answer is None:
        return {}
    if isinstance(answer, str):
        return {"type": answer}
    if not isinstance(answer, dict):
        return {}

    if "answers" in answer and isinstance(answer["answers"], dict):
        return {"type": "answers", "answers": answer["answers"]}

    if "decision" in answer:
        decision = answer["decision"]
        if isinstance(decision, str):
            return {"type": decision}
        if isinstance(decision, dict):
            return {
                "type": decision.get("type") or decision.get("action") or "approve",
                "patch": decision.get("patch") or {},
                "message": decision.get("message") or "",
            }

    if answer.get("type") in VALID_DECISIONS:
        return {
            "type": answer.get("type"),
            "patch": answer.get("patch") or {},
            "message": answer.get("message") or "",
        }

    return {}


def apply_patch(args: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """把员工/审批人改过的字段合并进参数（一层字典合并即可）。"""
    merged = dict(args or {})
    for key, value in (patch or {}).items():
        merged[key] = value
    return merged


def patch_action(action: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """人在卡片上改的参数，直接写回 action.args（全项目只有这一份参数，不另存草稿）。"""
    if not patch:
        return dict(action or {})
    args = apply_patch(action.get("args") or {}, patch)
    sources = dict(action.get("sources") or {})
    for key in patch:
        sources[key] = "from_user"  # 人改过的值，来源就是人
    return {**action, "args": args, "sources": sources}


def _citations(state: TicketState) -> list[str]:
    """卡片上展示的制度依据（引用串已在证据层拼好）。"""
    return [str(item.get("citation") or "") for item in (state.get("policy_evidence") or []) if item]


def _thread_id(state: TicketState) -> str:
    """当前会话 id（`initial_state` 写入）。

    审批中心靠它把 pending 记录映射回会话：没有它，主管点了"通过"也不知道 resume 哪条 thread。
    CLI 直连时可能为空，此时留痕照写，只是前端无法一键恢复。
    """
    return str(state.get("thread_id") or "")


# --------------------------------------------------------------------------- #
# 二、审批留痕（三处闸门共用的"业务事实"落库）
# --------------------------------------------------------------------------- #
def approval_target(action: dict[str, Any]) -> str:
    """这次审批针对什么：优先工单号，其次标题，最后用摘要兜底。"""
    args = (action or {}).get("args") or {}
    return str(args.get("ticket_no") or args.get("title") or summary_of(action))


def record_approval(
    actor: dict[str, Any],
    action: dict[str, Any],
    status: str,
    *,
    risk: str,
    note: str = "",
    approver: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    """把这次闸门的留痕写到工单 server（pending / approved / edited / rejected）。

    返回审批行本身（含 requester / id）；写失败返回空 dict。
    为什么要返回值：节点被 interrupt 恢复时会**重放**，此时 runtime.context 已经是恢复人，
    发起人只能从服务端那行 pending 里读回来（否则会把审批人当成发起人）。
    为什么带 thread_id：审批中心的"通过/驳回"要拿它 resume 对应会话。
    """
    try:
        data = ticket_tools.save_approval(
            actor,
            op=str((action or {}).get("op") or "unknown"),
            target=approval_target(action),
            risk=risk,
            status=status,
            summary=summary_of(action),
            note=note,
            approver=approver,
            thread_id=thread_id,
        )
    except Exception:  # noqa: BLE001 - 留痕失败不阻断业务
        logger.warning("审批留痕写入失败（不影响主流程）", exc_info=True)
        return {}
    approval = (data or {}).get("approval") or {}
    return approval if isinstance(approval, dict) else {}


# --------------------------------------------------------------------------- #
# 三、确认门：可撤销动作，提单人本人点一下
# --------------------------------------------------------------------------- #
def confirm_action(state: TicketState, runtime: Runtime[UserContext]) -> dict[str, Any]:
    """可撤销的动作，让提单人本人看一眼参数再点确认。"""
    action = state.get("action") or {}
    risk = str(state.get("risk") or "read")
    context = runtime.context
    actor = actor_of(runtime)

    pending = record_approval(
        actor, action, "pending", risk=risk, thread_id=_thread_id(state)
    )  # 幂等：重放不会重复插
    requested_by = str(pending.get("requester") or context.user_id)

    payload = {
        "type": "confirm",
        "title": summary_of(action),
        "fields": fields_of(action),
        "citations": _citations(state),
        "risk": risk,
        "hint": "确认后才会真正写入系统；发现填错了可以直接改字段。",
    }
    answer = interrupt(payload)

    # 这一步只等提单人本人；别人 resume 进来直接回一句结束，不替他确认、也不挂起
    if runtime.context.user_id != requested_by:
        return {
            "outcome": "denied",
            "reply": (
                f"这一步只等提单人本人（{requested_by}）确认，当前身份不能替他确认。"
                "需要继续的话，让本人拿同一条 thread resume。"
            ),
        }

    parsed = normalize_human_input(answer)
    kind = parsed.get("type") or "approve"
    record_approval(
        actor,
        action,
        DECISION_STATUS.get(kind, "rejected"),
        risk=risk,
        note=parsed.get("message") or "",
        approver=runtime.context.user_id,
        thread_id=_thread_id(state),
    )

    if kind == "reject":
        message = parsed.get("message") or "员工取消了这次操作"
        return {
            "outcome": "rejected",
            "reply": f"{label_of(action)}没有执行：{message}。需要的话换个说法再来一次。",
        }

    patch = parsed.get("patch") or {}
    action_patched = patch_action(action, patch)
    op = str(action_patched.get("op") or "")
    # 关键：按"改完之后的参数"重算风险，勾出不可逆参数就升级到审批门
    new_risk = compute_risk(op, action_patched.get("args") or {}, RISK_BY_OP.get(op, "write_reversible"))
    gate = GATE_BY_RISK.get(new_risk, "confirm")
    return {"action": action_patched, "risk": new_risk, "gate": gate}


# --------------------------------------------------------------------------- #
# 四、审批门：不可逆 / 全员可见动作，有权限的人点头
# --------------------------------------------------------------------------- #
def resolve_approver(op: str, roles: tuple[str, ...]) -> tuple[bool, list[str], str]:
    allowed_roles, label = APPROVER_ROLES.get(op, DEFAULT_APPROVER)
    ok = any(role in allowed_roles for role in roles)
    return ok, list(allowed_roles), label


def approve_action(state: TicketState, runtime: Runtime[UserContext]) -> dict[str, Any]:
    """审批闸门：发起人一律进 pending 队列；恢复时按恢复人的身份决定能不能点。"""
    context = runtime.context
    action = state.get("action") or {}
    actor = actor_of(runtime)
    op = str(action.get("op") or "")
    risk = str(state.get("risk") or "read")

    pending = record_approval(
        actor, action, "pending", risk=risk, thread_id=_thread_id(state)
    )
    requested_by = str(pending.get("requester") or context.user_id)

    can_decide, allowed_roles, approver_label = resolve_approver(op, tuple(context.roles))
    payload = {
        "type": "approve",
        "mode": "decide" if can_decide else "request",
        "requested_by": requested_by,
        "title": summary_of(action),
        "fields": fields_of(action),
        "citations": _citations(state),
        "risk": risk,
        "required_roles": allowed_roles,
        "hint": (
            "发布后全员可见，且不能撤回；请确认内容与引用都站得住。"
            if op == "publish_kb_article"
            else "关闭并通知提单人后撤不回；请确认解决说明写得清楚。"
        )
        if can_decide
        else f"已提交给{approver_label}审批。把 thread 交给有权限的同事，用同一条 thread resume 即可继续。",
    }
    answer = interrupt(payload)

    # 恢复时可能是另一个人（主管）。没有审批权的人点了 → 直接回一句结束，不替他做决定
    decider = runtime.context
    decider_can, _, decider_label = resolve_approver(op, tuple(decider.roles))
    if not decider_can:
        return {
            "outcome": "denied",
            "reply": (
                f"这件事要{decider_label}审批，当前身份（" + "、".join(decider.roles) + "）不能点通过。"
                f"发起人：{requested_by}。请让有权限的同事拿同一条 thread resume。"
            ),
        }

    parsed = normalize_human_input(answer)
    kind = parsed.get("type") or "approve"
    self_approved = requested_by == decider.user_id
    record_approval(
        actor,
        action,
        DECISION_STATUS.get(kind, "rejected"),
        risk=risk,
        note=("自审" if self_approved else "") + (parsed.get("message") or ""),
        approver=decider.user_id,
        thread_id=_thread_id(state),
    )
    approval = {
        "approver": decider.user_id,
        "roles": list(decider.roles),
        "required_roles": allowed_roles,
        "requested_by": requested_by,
        "self_approved": self_approved,
    }

    if kind == "reject":
        message = parsed.get("message") or "审批未通过"
        return {
            "approval": approval,
            "outcome": "rejected",
            "reply": f"{summary_of(action)}没有通过审批：{message}。需要的话改完再提一次。",
        }

    action_patched = patch_action(action, parsed.get("patch") or {})
    return {"action": action_patched, "approval": approval}
