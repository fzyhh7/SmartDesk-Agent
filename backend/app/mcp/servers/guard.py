"""工具层鉴权（server 侧，Agent 不可信）。

为什么权限必须放在 MCP server 里（面试要能讲）：
- Agent 手里的 tenant_id / reporter 是模型"填"的参数，模型可能填错，也可能被提示词攻击改写；
- 工具是真正改数据的地方，谁调用、以什么身份调用，只能由**服务端**按身份再判一次；
- 所以每个工具都要求传 `actor`（身份票据），server 用它覆盖 tenant/reporter，并按规则判定能不能做。

身份票据结构（由 Agent 从 Runtime Context 生成，绝不从模型输出里取）：
    {"user_id": "u-1002", "tenant_id": "tenant-demo", "roles": ["employee"]}

角色与权限：
- employee   只能读/改/关**自己提的单**；列单只能列自己的；不能发布知识
- approver   能读/改/关本租户所有单（审批人视角）
- kb_owner   能发布知识文章（审批通过后）
- 跨租户一律拒绝
"""

from __future__ import annotations

import json
from typing import Any

VALID_ROLES = ("employee", "approver", "kb_owner")
PRIVILEGED_ROLES = {"approver"}
KB_PUBLISHER_ROLES = {"kb_owner"}


def normalize_actor(actor: Any) -> dict[str, Any] | None:
    """把调用方传来的 actor 规整成身份票据；不合法返回 None（就当未认证）。"""
    if isinstance(actor, str) and actor.strip():
        try:
            actor = json.loads(actor)
        except json.JSONDecodeError:
            return None
    if not isinstance(actor, dict):
        return None
    user_id = str(actor.get("user_id") or "").strip()
    tenant_id = str(actor.get("tenant_id") or "").strip()
    if not user_id or not tenant_id:
        return None
    roles = tuple(str(role) for role in (actor.get("roles") or ()) if str(role) in VALID_ROLES)
    return {"user_id": user_id, "tenant_id": tenant_id, "roles": roles or ("employee",)}


def deny(code: str, reason: str, **extra: Any) -> str:
    """统一的拒绝响应：机器可读 error.code + 给人看的中文 reason。"""
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "reason": reason}}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def require_actor(actor: Any) -> tuple[dict[str, Any] | None, str | None]:
    """返回 (票据, 拒绝响应)。票据为 None 时调用方应直接把拒绝响应返回给 Agent。"""
    normalized = normalize_actor(actor)
    if normalized is None:
        return None, deny("unauthorized", "缺少调用方身份（actor），拒绝执行", need="user_id / tenant_id")
    return normalized, None


def is_privileged(actor: dict[str, Any]) -> bool:
    return bool(PRIVILEGED_ROLES & set(actor["roles"]))


def can_publish_kb(actor: dict[str, Any]) -> bool:
    return bool(KB_PUBLISHER_ROLES & set(actor["roles"]))


def same_tenant(actor: dict[str, Any], record: dict[str, Any]) -> bool:
    return str(record.get("tenant_id") or "") == actor["tenant_id"]


def can_read_ticket(actor: dict[str, Any], record: dict[str, Any]) -> bool:
    """同租户 + （特权角色 / 本人提单）。"""
    if not same_tenant(actor, record):
        return False
    return is_privileged(actor) or str(record.get("reporter") or "") == actor["user_id"]


def can_write_ticket(actor: dict[str, Any], record: dict[str, Any]) -> bool:
    """改/关与读同一条规则：自己的单能处理，审批人能处理本租户任意单。"""
    return can_read_ticket(actor, record)


def notify_reports_self(actor: dict[str, Any], record: dict[str, Any]) -> bool:
    """通知对象就是操作者自己 → 这个通知没有意义（不用为它升级成不可逆）。"""
    return str(record.get("reporter") or "") == actor["user_id"]


def ticket_flags(actor: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """给读接口附上"这张单你能做什么"的判定结果。

    规则留在 server（Agent 不可信），节点只读结果、不重复实现一遍权限。
    """
    return {
        "can_write": can_write_ticket(actor, record),
        "notify_reports_self": notify_reports_self(actor, record),
    }