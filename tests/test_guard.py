"""工具层鉴权的单元测试。

这是整个项目「Agent 不可信」假设的落点：谁在调、以什么身份调，由 server 侧再判一次。
这些函数只吃两个 dict（actor 票据 + 数据库行），不碰 SQLite、不碰 MCP 传输，可以直接断言。
"""

from __future__ import annotations

import json

import pytest

from backend.app.mcp.servers.guard import (
    can_publish_kb,
    can_read_ticket,
    can_write_ticket,
    deny,
    is_privileged,
    normalize_actor,
    notify_reports_self,
    require_actor,
    same_tenant,
    ticket_flags,
)

EMPLOYEE = {"user_id": "u-1001", "tenant_id": "tenant-demo", "roles": ("employee",)}
APPROVER = {"user_id": "u-9001", "tenant_id": "tenant-demo", "roles": ("approver",)}
KB_OWNER = {"user_id": "u-3001", "tenant_id": "tenant-demo", "roles": ("kb_owner",)}
OTHER_TENANT = {"user_id": "u-9001", "tenant_id": "tenant-other", "roles": ("approver",)}

OWN_TICKET = {"ticket_no": "TK-1", "tenant_id": "tenant-demo", "reporter": "u-1001"}
OTHERS_TICKET = {"ticket_no": "TK-2", "tenant_id": "tenant-demo", "reporter": "u-2001"}
OTHER_TENANT_TICKET = {"ticket_no": "TK-3", "tenant_id": "tenant-other", "reporter": "u-1001"}


# --------------------------------------------------------------------------- #
# normalize_actor：票据规整（这是唯一入口，模型输出过不了这里就进不来）
# --------------------------------------------------------------------------- #


def test_normalize_accepts_dict():
    assert normalize_actor({"user_id": "u-1", "tenant_id": "t-1", "roles": ["employee"]}) == {
        "user_id": "u-1",
        "tenant_id": "t-1",
        "roles": ("employee",),
    }


def test_normalize_accepts_json_string():
    raw = json.dumps({"user_id": "u-1", "tenant_id": "t-1", "roles": ["approver"]})
    assert normalize_actor(raw)["roles"] == ("approver",)


@pytest.mark.parametrize(
    "actor",
    [
        None,
        "",
        "{not json}",  # 坏 JSON
        {"user_id": "u-1"},  # 缺 tenant
        {"tenant_id": "t-1"},  # 缺 user
        {"user_id": "  ", "tenant_id": "t-1"},  # 空白也算缺
        ["u-1"],  # 类型不对
    ],
)
def test_normalize_rejects_bad_actor(actor):
    assert normalize_actor(actor) is None


def test_normalize_drops_unknown_roles_and_defaults_to_employee():
    """未知角色（比如模型瞎编的 "admin"）必须被丢掉，不能悄悄提权。"""
    normalized = normalize_actor({"user_id": "u-1", "tenant_id": "t-1", "roles": ["admin", "employee"]})
    assert normalized["roles"] == ("employee",)

    no_roles = normalize_actor({"user_id": "u-1", "tenant_id": "t-1"})
    assert no_roles["roles"] == ("employee",)


# --------------------------------------------------------------------------- #
# require_actor / deny：统一拒绝响应
# --------------------------------------------------------------------------- #


def test_require_actor_returns_ticket_when_valid():
    actor, error = require_actor(EMPLOYEE)
    assert error is None
    assert actor["user_id"] == "u-1001"


def test_require_actor_denies_when_missing():
    actor, error = require_actor(None)
    assert actor is None
    payload = json.loads(error)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unauthorized"


def test_deny_carries_machine_code_and_human_reason():
    payload = json.loads(deny("forbidden", "只有 owner 能发布", hint="找主管"))
    assert payload["error"] == {"code": "forbidden", "reason": "只有 owner 能发布"}
    assert payload["hint"] == "找主管"


# --------------------------------------------------------------------------- #
# 角色判定
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("actor", "privileged"),
    [(APPROVER, True), (EMPLOYEE, False), (KB_OWNER, False)],
)
def test_is_privileged(actor, privileged):
    assert is_privileged(actor) is privileged


@pytest.mark.parametrize(
    ("actor", "allowed"),
    [(KB_OWNER, True), (EMPLOYEE, False), (APPROVER, False)],
)
def test_can_publish_kb(actor, allowed):
    """发布知识只有 kb_owner 能做；审批人也不行（角色不能互相顶替）。"""
    assert can_publish_kb(actor) is allowed


def test_same_tenant():
    assert same_tenant(EMPLOYEE, OWN_TICKET) is True
    assert same_tenant(OTHER_TENANT, OWN_TICKET) is False
    assert same_tenant(EMPLOYEE, {"tenant_id": None}) is False


# --------------------------------------------------------------------------- #
# 工单读写权限矩阵：同租户 + （特权 / 本人）
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("actor", "record", "expected"),
    [
        (EMPLOYEE, OWN_TICKET, True),  # 自己的单
        (EMPLOYEE, OTHERS_TICKET, False),  # 别人的单
        (APPROVER, OTHERS_TICKET, True),  # 审批人看本租户任意单
        (APPROVER, OTHER_TENANT_TICKET, False),  # 跨租户一律拒绝（哪怕是审批人）
        (KB_OWNER, OTHERS_TICKET, False),  # kb_owner 不是工单特权角色
        (EMPLOYEE, OTHER_TENANT_TICKET, False),  # 自己提的单也不行——租户隔离优先
    ],
)
def test_can_read_ticket_matrix(actor, record, expected):
    assert can_read_ticket(actor, record) is expected


def test_write_has_the_same_rule_as_read():
    """改/关与读同一条规则（能看才能动），这条不许悄悄放宽。"""
    for actor in (EMPLOYEE, APPROVER, KB_OWNER):
        for record in (OWN_TICKET, OTHERS_TICKET, OTHER_TENANT_TICKET):
            assert can_write_ticket(actor, record) == can_read_ticket(actor, record)


# --------------------------------------------------------------------------- #
# 通知对象是自己 → 这个通知没有意义
# --------------------------------------------------------------------------- #


def test_notify_reports_self():
    """自己关自己的单还勾「通知提单人」，不该因此把它升级成不可逆。"""
    assert notify_reports_self(EMPLOYEE, OWN_TICKET) is True
    assert notify_reports_self(EMPLOYEE, OTHERS_TICKET) is False
    assert notify_reports_self(APPROVER, OTHERS_TICKET) is False


def test_ticket_flags_shape():
    assert ticket_flags(EMPLOYEE, OWN_TICKET) == {
        "can_write": True,
        "notify_reports_self": True,
    }
    assert ticket_flags(EMPLOYEE, OTHERS_TICKET) == {
        "can_write": False,
        "notify_reports_self": False,
    }
