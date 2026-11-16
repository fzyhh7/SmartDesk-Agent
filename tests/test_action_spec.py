"""风险规格表与动作视图的单元测试。

这些都是纯函数（不碰网络、不碰 Milvus、不碰 LLM），所以能在 CI 里秒级跑完。
覆盖的是「改一行表就会破坏语义」的地方：风险升级规则、闸门映射、卡片字段可编辑性。
"""

from __future__ import annotations

import pytest

from backend.app.agents.nodes.action_spec import (
    EDITABLE_BLOCK,
    GATE_BY_RISK,
    RISK_BY_OP,
    compute_risk,
    fields_of,
    label_of,
    server_of,
    summary_of,
)

# --------------------------------------------------------------------------- #
# compute_risk：风险不只由「调哪个工具」决定，还要看「带什么参数」
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("op", "args", "base", "expected"),
    [
        # 只读：不会改数据，直通执行
        ("query_ticket", {}, "read", "read"),
        ("list_tickets", {}, "read", "read"),
        ("search_kb", {}, "read", "read"),
        # 可逆写：默认这一档
        ("create_ticket", {}, "write_reversible", "write_reversible"),
        ("update_ticket", {}, "write_reversible", "write_reversible"),
        # close_ticket 不通知 = 可逆（能重开）
        ("close_ticket", {"notify_reporter": False}, "write_reversible", "write_reversible"),
        ("close_ticket", {}, "write_reversible", "write_reversible"),
        # close_ticket + 通知提单人 = 消息发出去撤不回 → 不可逆
        ("close_ticket", {"notify_reporter": True}, "write_reversible", "write_irreversible"),
        # 发布知识文章：发布后全员可见 → 不可逆
        ("publish_kb_article", {}, "write_irreversible", "write_irreversible"),
        ("publish_kb_article", {}, "read", "write_irreversible"),
    ],
)
def test_compute_risk_upgrades_by_args(op, args, base, expected):
    assert compute_risk(op, args, base) == expected


def test_close_ticket_without_notify_stays_reversible_but_with_notify_upgrades():
    """同一 op、只差一个参数，风险档位必须不同——这是本项目最关键的一条业务规则。"""
    quiet = compute_risk("close_ticket", {"notify_reporter": False}, "write_reversible")
    noisy = compute_risk("close_ticket", {"notify_reporter": True}, "write_reversible")
    assert quiet == "write_reversible"
    assert noisy == "write_irreversible"
    assert quiet != noisy


def test_compute_risk_falls_back_to_base_for_unknown_op():
    """未知 op 不动 base（genuine 的兜底应该是「按调用方给的默认档」，不是悄悄变成只读）。"""
    assert compute_risk("some_new_tool", {}, "write_reversible") == "write_reversible"


# --------------------------------------------------------------------------- #
# GATE_BY_RISK：三档风险必须一一对应三道闸门
# --------------------------------------------------------------------------- #


def test_gate_mapping_is_complete_and_unique():
    assert GATE_BY_RISK == {
        "read": "execute",
        "write_reversible": "confirm",
        "write_irreversible": "approve",
    }
    # 三档各去不同节点，不能有两个风险共用一道门
    assert len(set(GATE_BY_RISK.values())) == len(GATE_BY_RISK)


@pytest.mark.parametrize("op", sorted(RISK_BY_OP))
def test_every_known_op_has_a_gate(op):
    """表里每个 op 的风险档位都要能在 GATE_BY_RISK 里找到下一跳，否则图会断。"""
    risk = compute_risk(op, {}, RISK_BY_OP[op])
    assert risk in GATE_BY_RISK


# --------------------------------------------------------------------------- #
# server_of：op → 哪个 MCP server（唯一推导入口）
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("op", "server"),
    [
        ("search_kb", "kb"),
        ("publish_kb_article", "kb"),
        ("query_ticket", "ticket"),
        ("close_ticket", "ticket"),
        ("", "ticket"),  # 空 op 走默认 server，不能抛异常
    ],
)
def test_server_of(op, server):
    assert server_of(op) == server


# --------------------------------------------------------------------------- #
# 中文标签 / 摘要 / 卡片字段
# --------------------------------------------------------------------------- #


def test_label_of_defaults_when_missing():
    assert label_of({"label": "关工单"}) == "关工单"
    assert label_of({}) == "操作"


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        # 标题里已经带了「建工单：」前缀 → 摘要不能重复成「建工单：建工单：…」
        ({"label": "建工单", "args": {"title": "建工单：打印机连不上"}}, "建工单：打印机连不上"),
        ({"label": "建工单", "args": {"title": "打印机连不上"}}, "建工单：打印机连不上"),
        ({"label": "关工单", "args": {"ticket_no": "TK-1"}}, "关工单：TK-1"),
        # 没有可用标题 → 只给动作名，不留一个光秃秃的冒号
        ({"label": "列工单", "args": {}}, "列工单"),
    ],
)
def test_summary_of_dedupes_label(action, expected):
    assert summary_of(action) == expected


def test_fields_of_marks_identity_fields_readonly():
    """reporter / tenant_id 是身份字段，卡片上不许改（否则等于让人改自己的身份）。"""
    fields = fields_of(
        {
            "label": "建工单",
            "args": {"title": "打印机连不上", "reporter": "u-1001", "tenant_id": "tenant-demo"},
            "sources": {"title": "from_user"},
        }
    )
    by_name = {f["name"]: f for f in fields}

    assert by_name["title"]["label"] == "标题"
    assert by_name["title"]["source"] == "from_user"
    assert by_name["title"]["editable"] is True

    for name in EDITABLE_BLOCK:
        assert by_name[name]["editable"] is False, f"{name} 必须只读"

    # 没给 sources 的字段默认标记为「模型推断」，前端据此提示用户核对
    assert by_name["reporter"]["source"] == "agent_inferred"


def test_fields_of_keeps_arg_order():
    """"卡片字段顺序跟着 args 走（人的眼睛按「标题 → 描述 → 优先级」读更顺）。"""
    fields = fields_of({"args": {"title": "A", "description": "B", "urgency": "高"}})
    assert [f["name"] for f in fields] == ["title", "description", "urgency"]
