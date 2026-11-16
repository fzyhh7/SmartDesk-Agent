"""路由：每个条件边配一个纯函数，`graph.py` 只负责把节点和边装配起来。

为什么单独一个文件（而不是写在 graph.py 里）：
- 这五个函数不碰 LangGraph、不碰网络、不碰 State 的具体类型，只读几个字段做判断，
  `tests/test_routing.py` 可以直接断言「什么状态 → 下一跳是谁」，不需要装 langgraph；
- 分支决策集中在一处，改路由只改这里，节点内部不出现跳转逻辑。

两处最容易讲错（面试常问）：
- `route_after_confirm` 不是「确认完就执行」：员工可能在卡片上改出**不可逆**参数
  （关单时勾"通知提单人"），所以确认后要按新参数重算风险，需要时补一道 approve_action。
- 三个闸门节点的 `interrupt()` 让图停下来；恢复后走 `route_after_human`，
  没批就回复、批过了才执行。
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

# gate → 节点名：plan_action 只写 gate（clarify/confirm/approve/execute），不决定去哪
GATE_TO_NODE: dict[str, str] = {
    "clarify": "ask_missing_info",
    "confirm": "confirm_action",
    "approve": "approve_action",
    "execute": "execute_action",
}


def route_after_classify(
    state: Mapping[str, Any],
) -> Literal["compose_reply", "gather_evidence"]:
    """闲聊不查资料；其余都要先取证据。"""
    return "compose_reply" if state.get("intent") == "chat" else "gather_evidence"


def route_after_gather(
    state: Mapping[str, Any],
) -> Literal["plan_action", "answer_with_citations"]:
    """要动手（动作型）才进 plan_action；问知识直接答。"""
    return "plan_action" if state.get("intent") == "action" else "answer_with_citations"


def route_after_plan(
    state: Mapping[str, Any],
) -> Literal[
    "compose_reply", "ask_missing_info", "confirm_action", "approve_action", "execute_action"
]:
    """没办成（denied / rejected / not_found）→ 直接回复；否则按 gate 进对应的门。"""
    if state.get("outcome"):
        return "compose_reply"
    gate = state.get("gate") or "execute"
    return GATE_TO_NODE.get(gate, "execute_action")  # type: ignore[return-value]


def route_after_confirm(
    state: Mapping[str, Any],
) -> Literal["compose_reply", "approve_action", "execute_action"]:
    """被拒/没资格 → 回复；改出不可逆参数（gate 升成 approve）→ 补一道审批；否则直接执行。"""
    if state.get("outcome"):
        return "compose_reply"
    return "approve_action" if state.get("gate") == "approve" else "execute_action"


def route_after_human(
    state: Mapping[str, Any],
) -> Literal["compose_reply", "execute_action"]:
    """没人批 / 执行前就失败 → 回复；批过了 → 执行。"""
    return "compose_reply" if state.get("outcome") else "execute_action"
