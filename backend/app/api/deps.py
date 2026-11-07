"""请求头 → UserContext（这一层只做"身份解析"，不判权限）。

为什么用请求头而不是 JWT：
- 这个项目的重点是 Agent 编排，登录/发 token 属于"企业接入层"，可以后补；
- 但"身份只能从请求进入、不能从模型输出进入"这条必须现在就立住——
  `UserContext` 是唯一可信身份来源，模型或 State 里填的角色一律不认。
换成 JWT 时只改这里：解析 token → 取出 user_id/tenant_id/roles，其它代码一行不用动。
"""

from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException

from ..agents.state import UserContext

# 演示用默认身份（不传请求头时按这个走，方便 curl 直接调）
DEFAULT_USER = "u-1001"
DEFAULT_TENANT = "tenant-demo"
VALID_ROLES = {"employee", "approver", "kb_owner"}


def actor_of_context(context: UserContext) -> dict[str, Any]:
    """`UserContext` → MCP 工具认的票据（和节点里 `state.actor_of(runtime)` 同一个形状）。"""
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "roles": list(context.roles),
    }


def get_context(
    x_user_id: str = Header(default=DEFAULT_USER, alias="X-User-Id"),
    x_tenant_id: str = Header(default=DEFAULT_TENANT, alias="X-Tenant-Id"),
    x_roles: str = Header(default="employee", alias="X-Roles"),
) -> UserContext:
    """把三个请求头规范化成 `UserContext`（角色白名单过滤，空则降级成 employee）。"""
    roles = tuple(
        part.strip()
        for part in (x_roles or "").replace(" ", "").split(",")
        if part.strip() in VALID_ROLES
    )
    if not x_user_id.strip():
        raise HTTPException(status_code=400, detail="X-User-Id 不能为空")
    if not x_tenant_id.strip():
        raise HTTPException(status_code=400, detail="X-Tenant-Id 不能为空")
    return UserContext(
        user_id=x_user_id.strip(),
        tenant_id=x_tenant_id.strip(),
        roles=roles or ("employee",),
        display_name=x_user_id.strip(),
    )
