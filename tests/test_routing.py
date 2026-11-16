"""路由函数的单元测试：断言「什么状态 → 下一跳是谁」。

路由是纯函数（只读几个字段），所以不用起 langgraph、不用连 checkpoint 就能测。
这些断言的价值在于：改动节点里写哪个字段时，路由的行为会立刻被钉住。
"""

from __future__ import annotations

import pytest

from backend.app.agents.routing import (
    GATE_TO_NODE,
    route_after_classify,
    route_after_confirm,
    route_after_gather,
    route_after_human,
    route_after_plan,
)

# --------------------------------------------------------------------------- #
# classify → 闲聊直接回复；其余先取证
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("intent", "next_node"),
    [
        ("chat", "compose_reply"),
        ("knowledge", "gather_evidence"),
        ("action", "gather_evidence"),
        (None, "gather_evidence"),  # 没判出来也先取证，不能把用户丢给一句闲聊
    ],
)
def test_route_after_classify(intent, next_node):
    assert route_after_classify({"intent": intent}) == next_node


# --------------------------------------------------------------------------- #
# gather → 动作型进 plan；知识型直接答
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("intent", "next_node"),
    [
        ("action", "plan_action"),
        ("knowledge", "answer_with_citations"),
        ("chat", "answer_with_citations"),
    ],
)
def test_route_after_gather(intent, next_node):
    assert route_after_gather({"intent": intent}) == next_node


# --------------------------------------------------------------------------- #
# plan → 没办成直接回复；否则按 gate 进对应的门
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("outcome", ["denied", "not_found", "rejected", "failed"])
def test_route_after_plan_short_circuits_on_outcome(outcome):
    """已经没办成（越权 / 查不到 / 被拒）就别再去敲门，直接回复。"""
    assert route_after_plan({"outcome": outcome, "gate": "confirm"}) == "compose_reply"


@pytest.mark.parametrize(("gate", "next_node"), sorted(GATE_TO_NODE.items()))
def test_route_after_plan_follows_gate(gate, next_node):
    assert route_after_plan({"gate": gate}) == next_node


def test_route_after_plan_defaults_to_execute():
    """gate 缺失（老 checkpoint）时按最保守以外的默认档走 execute——真正的高危动作
    在 execute_action 里还有一道兜底复核，所以这里不会漏掉不可逆写。"""
    assert route_after_plan({}) == "execute_action"
    assert route_after_plan({"gate": ""}) == "execute_action"


def test_route_after_plan_falls_back_for_unknown_gate():
    assert route_after_plan({"gate": "something_new"}) == "execute_action"


# --------------------------------------------------------------------------- #
# confirm → 改出不可逆参数要补一道审批
# --------------------------------------------------------------------------- #


def test_route_after_confirm_escalates_when_gate_became_approve():
    """员工在确认卡上勾了「通知提单人」→ 风险升成不可逆 → 必须再走审批。"""
    assert route_after_confirm({"gate": "approve"}) == "approve_action"


@pytest.mark.parametrize("gate", ["execute", "confirm", ""])
def test_route_after_confirm_executes_when_still_reversible(gate):
    assert route_after_confirm({"gate": gate}) == "execute_action"


def test_route_after_confirm_short_circuits_on_outcome():
    assert route_after_confirm({"outcome": "rejected", "gate": "approve"}) == "compose_reply"


# --------------------------------------------------------------------------- #
# human（三个闸门恢复之后）→ 批了就执行，没批就回复
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("state", "next_node"),
    [
        ({}, "execute_action"),
        ({"approved": True}, "execute_action"),
        ({"outcome": "rejected"}, "compose_reply"),
        ({"outcome": "denied"}, "compose_reply"),
        ({"outcome": "not_found"}, "compose_reply"),
    ],
)
def test_route_after_human(state, next_node):
    assert route_after_human(state) == next_node


# --------------------------------------------------------------------------- #
# 闸门表本身
# --------------------------------------------------------------------------- #


def test_gate_table_maps_four_gates():
    assert GATE_TO_NODE == {
        "clarify": "ask_missing_info",
        "confirm": "confirm_action",
        "approve": "approve_action",
        "execute": "execute_action",
    }


def test_every_router_returns_a_real_node_name():
    """路由返回值必须是图里真实存在的节点名，否则 LangGraph 装配时才报错。"""
    nodes = {
        "classify_request",
        "gather_evidence",
        "answer_with_citations",
        "plan_action",
        "ask_missing_info",
        "confirm_action",
        "approve_action",
        "execute_action",
        "compose_reply",
    }
    returned = {
        route_after_classify({"intent": "chat"}),
        route_after_classify({"intent": "action"}),
        route_after_gather({"intent": "action"}),
        route_after_gather({"intent": "knowledge"}),
        route_after_plan({"outcome": "denied"}),
        route_after_plan({"gate": "clarify"}),
        route_after_confirm({"gate": "approve"}),
        route_after_confirm({"gate": "execute"}),
        route_after_human({}),
        route_after_human({"outcome": "rejected"}),
        *GATE_TO_NODE.values(),
    }
    assert returned <= nodes
