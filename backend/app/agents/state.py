"""主图状态（State）与调用上下文（Context）。

设计要点：
- State 用 TypedDict（继承 AgentState，已内置 messages + add_messages reducer）
- Context（每次调用只读：谁 / 哪个租户 / 什么角色）与 State（图内可变）严格分离，Context 不落盘到 checkpoint
- State 只保留下游决策需要、且无法由现有字段直接推导出来的最小字段集

本项目把"一次请求"拆成三件事，State 也按这三件事分组：
1. 理解：intent / action / risk
2. 证据：policy_evidence（制度、手册召回）+ facts（对象事实，如工单详情）
3. 动作：action（参数唯一真相） -> gate（走哪个闸门） -> approval（谁批的） -> result
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from langchain.agents import AgentState

# 三种意图：知识问答 / 动作请求 / 闲聊
Intent = Literal["knowledge", "action", "chat"]
# 三个闸门 + 直通
Gate = Literal["clarify", "confirm", "approve", "execute"]
# 风险等级：只读 / 可撤销写 / 不可逆或全员可见
Risk = Literal["read", "write_reversible", "write_irreversible"]


@dataclass(frozen=True)
class UserContext:
    """调用上下文：一次 invoke 内只读，不写进 checkpoint。"""

    user_id: str
    tenant_id: str
    # employee=普通员工；approver=主管；kb_owner=知识库 owner
    roles: tuple[str, ...] = field(default_factory=lambda: ("employee",))
    display_name: str = "同事"

    @property
    def can_publish_kb(self) -> bool:
        return bool({"kb_owner"} & set(self.roles))


class TicketState(AgentState):
    """主图状态。AgentState 已包含 messages / jump_to / structured_response。"""

    # ---------- 身份与输入 ----------
    # thread_id 写进 State 是为了让审批留痕能带上"哪条会话"，审批中心才知道 resume 哪一条
    thread_id: str
    tenant_id: str
    user_id: str
    query: str

    # ---------- 第 1 步：理解 ----------
    intent: str
    # 动作（唯一真相）：{"server","op","label","args","missing","sources"}
    # args 是"定稿参数"：确认卡上改完的值直接写回这里，执行节点读它
    action: dict[str, Any] | None
    risk: str
    # 分类的补充信息：{"topic":..., "summary":..., "urgency":...}
    classification: dict[str, Any] | None

    # ---------- 第 2 步：证据（两个字段各写各的 key，没有并行分支，不需要 reducer） ----------
    policy_evidence: list[dict[str, Any]]
    facts: list[dict[str, Any]]

    # ---------- 第 3 步：动作 ----------
    gate: str
    approval: dict[str, Any] | None
    result: dict[str, Any] | None

    # ---------- 输出 ----------
    via: str | None
    reply: str | None
    # 只有"没办成"才写：rejected（人拒绝或没资格）/ failed（执行失败）；正常跑完是 None
    outcome: str | None


def actor_of(runtime: Any) -> dict[str, Any]:
    """把 Runtime Context 变成给 MCP server 的身份票据（server 侧鉴权的唯一可信来源）。

    为什么不能从 State / 模型输出取：那是"模型说的"，可能填错也可能被提示词攻击改写。
    """
    context = getattr(runtime, "context", None)
    if context is None:
        raise RuntimeError("缺少 UserContext：调用 invoke 时必须传 context=UserContext(...)")
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "roles": list(context.roles),
    }


def initial_state(
    *,
    tenant_id: str,
    user_id: str = "u-1001",
    query: str,
    thread_id: str = "",
    messages: list[Any] | None = None,
) -> dict[str, Any]:
    """构造一次 invoke 的初始输入（只传增量字段，其余由 LangGraph 补默认值）。"""
    return {
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "query": query,
        "intent": "",
        "action": None,
        "risk": "read",
        "classification": None,
        "policy_evidence": [],
        "facts": [],
        "gate": "execute",
        "approval": None,
        "result": None,
        "via": None,
        "reply": None,
        "outcome": None,
        "messages": messages or [],
    }