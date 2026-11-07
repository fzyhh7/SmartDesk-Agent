"""MCP 客户端：一个 MultiServerMCPClient 管两个 server（工单 / 知识库）。

设计要点：
- `MultiServerMCPClient({"ticket": {...}, "kb": {...}})` 一次装配多个独立 MCP server；
- stdio 连接需要 transport/command/args/env/cwd 五项；
- 工具是异步的，必须 `await tool.ainvoke(...)`，所以这里用一个同步门面 `call_tool()` 包住。

传输降级：沙箱/受限环境禁止起子进程时，
自动切到进程内模式（`fastmcp.Client(server.mcp)`）——协议一样、工具实现是同一份代码。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[4]
SERVERS: dict[str, dict[str, Any]] = {
    "ticket": {
        "script": ROOT_DIR / "backend" / "app" / "mcp" / "servers" / "ticket_server.py",
        "module": "backend.app.mcp.servers.ticket_server",
        "mcp_attr": "ticket_mcp",
    },
    "kb": {
        "script": ROOT_DIR / "backend" / "app" / "mcp" / "servers" / "kb_server.py",
        "module": "backend.app.mcp.servers.kb_server",
        "mcp_attr": "kb_mcp",
    },
}

# 工具中文名（CLI 的 tools 子命令与前端展示共用）。
# 注意：风险等级不在这里——唯一真相在 nodes/plan_action.py 的 RISK_BY_OP / compute_risk，
# 因为风险会随参数升级（close_ticket(notify_reporter=True) 才是不可逆），静态表记不住。
TOOL_CATALOG = {
    "query_ticket": {"label": "查工单"},
    "list_tickets": {"label": "列工单"},
    "create_ticket": {"label": "建工单"},
    "update_ticket": {"label": "改工单"},
    "close_ticket": {"label": "关工单"},
    "search_kb": {"label": "检索知识库"},
    "publish_kb_article": {"label": "发布知识文章"},
    "save_approval": {"label": "审批留痕"},
    "list_approvals": {"label": "审批中心"},
}

_KB_TOOLS = {"search_kb", "publish_kb_article"}
# 治理类工具（审批留痕/查询）：不进 plan_action 的 op 枚举，风险由服务端判，不参与业务风险分级
_GOVERNANCE_TOOLS = {"save_approval", "list_approvals"}

_TRANSPORT_MODE: str | None = os.environ.get("MCP_TRANSPORT", "").strip() or None  # None=自动
_CLIENT: MultiServerMCPClient | None = None

# 工单库路径：默认 .data/tickets.sqlite，允许用 TICKET_DB_PATH 覆盖（脚本/演示用副本库时靠它）。
# 必须在这里读一次并原样传给子进程——stdio 子进程的 env 是白名单构造的，
# 不显式透传的话 TICKET_DB_PATH 到了 server 里就会退回默认值，两边指向不同的库。
_DB_PATH = os.environ.get("TICKET_DB_PATH", "").strip() or str(ROOT_DIR / ".data" / "tickets.sqlite")


def transport_mode() -> str:
    return _TRANSPORT_MODE or "auto"


def transport_info() -> dict[str, Any]:
    return {
        "mode": transport_mode(),
        "python": sys.executable,
        "servers": {name: str(cfg["script"]) for name, cfg in SERVERS.items()},
        "hint": "stdio=独立进程；memory=进程内调用同一份 server 代码",
    }


def _switch_to_memory(reason: str) -> None:
    global _TRANSPORT_MODE, _CLIENT
    if _TRANSPORT_MODE == "memory":
        return
    logger.warning("stdio 不可用（%s），自动切换进程内模式", reason)
    _TRANSPORT_MODE = "memory"
    _CLIENT = None


def _connection_spec(server: str) -> dict[str, Any]:
    env = {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TICKET_DB_PATH": _DB_PATH,
    }
    return {
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(SERVERS[server]["script"])],
        "cwd": str(ROOT_DIR),
        "env": env,
    }


def get_client() -> MultiServerMCPClient:
    """进程内单例：一个客户端同时管理 ticket 与 kb 两个 MCP server。"""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = MultiServerMCPClient({name: _connection_spec(name) for name in SERVERS})
    return _CLIENT


def _is_permission_error(exc: BaseException) -> bool:
    """递归找 PermissionError / WinError 5（anyio 会把它们包进 ExceptionGroup）。"""
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, PermissionError):
            return True
        if getattr(current, "winerror", None) == 5:
            return True
        for attr in ("exceptions", "exceptions_", "__cause__", "__context__"):
            value = getattr(current, attr, None)
            if isinstance(value, BaseException):
                stack.append(value)
            elif isinstance(value, (list, tuple)):
                stack.extend(item for item in value if isinstance(item, BaseException))
    return False


def _text_of(item: Any) -> str:
    """从单个内容块里取文本（兼容 str / dict 块 / 带 text 属性的对象）。"""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("text") or "")
    return str(getattr(item, "text", "") or "")


def _parse_text(result: Any) -> dict[str, Any]:
    """把 MCP 返回的文本 JSON 解析成 dict（两个传输都返回 {"ok": ...} 文本）。

    兼容三种形状：ToolMessage、裸的 list[{"type": "text", "text": ...}]、以及直接返回的 dict。
    不同版本的 langchain-mcp-adapters 会在这三种之间变化，这里统一兜住。
    """
    if isinstance(result, dict) and "ok" in result:
        return result
    content = getattr(result, "content", None)
    blocks = content if content is not None else result
    for block in blocks if isinstance(blocks, (list, tuple)) else [blocks]:
        text = _text_of(block)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {"ok": False, "error": text}
        if isinstance(data, dict):
            return data
        return {"ok": False, "error": f"工具返回的不是对象：{data!r}"}
    for attr in ("data", "structured_content"):
        value = getattr(result, attr, None)
        if isinstance(value, dict):
            return value
    return {"ok": False, "error": f"无法解析的工具返回：{result!r}"}


def _server_module(server: str):
    return importlib.import_module(SERVERS[server]["module"])


def _call_stdio(server: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        tools = await get_client().get_tools(server_name=server)
        tool = next((item for item in tools if item.name == name), None)
        if tool is None:
            raise LookupError(f"{server} server 上没有工具 {name}")
        return _parse_text(await tool.ainvoke(args))

    return asyncio.run(run())


def _call_memory(server: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    from fastmcp import Client

    async def run() -> dict[str, Any]:
        mcp_instance = getattr(_server_module(server), SERVERS[server]["mcp_attr"])
        async with Client(mcp_instance) as client:
            result = await client.call_tool(name, args)
        return _parse_text(result)

    return asyncio.run(run())


def _run_in_thread(factory):
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(factory).result()


def _invoke(fn, server: str, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """在独立线程里跑一次异步调用（节点是同步函数，不能直接 await）。"""
    return _run_in_thread(lambda: fn(server, name, payload))


def call_tool(server: str, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """同步调用一个 MCP 工具；stdio 不可用时自动降级为进程内模式。"""
    if server not in SERVERS:
        return {"ok": False, "error": f"未知 server：{server}"}
    payload = dict(args or {})

    if _TRANSPORT_MODE != "memory":
        try:
            return _invoke(_call_stdio, server, name, payload)
        except Exception as exc:  # noqa: BLE001
            if not _is_permission_error(exc):
                return {"ok": False, "error": f"调用 {server}.{name} 失败：{exc}"}
            _switch_to_memory(str(exc))

    try:
        return _invoke(_call_memory, server, name, payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"调用 {server}.{name} 失败：{exc}"}


def tool_catalog() -> list[dict[str, Any]]:
    """列出两个 server 上的工具（名/中文名/读写/风险）。

    风险从 `nodes/plan_action.py` 的 RISK_BY_OP 取，全项目只保留这一份风险表。
    """
    from ..nodes.plan_action import RISK_BY_OP  # 延迟导入，避免 tools ↔ nodes 循环依赖

    items: list[dict[str, Any]] = []
    for name, meta in TOOL_CATALOG.items():
        server = "kb" if name in _KB_TOOLS else "ticket"
        risk = "governance" if name in _GOVERNANCE_TOOLS else RISK_BY_OP.get(name, "write_reversible")
        items.append({"server": server, "name": name, "risk": risk, **meta})
    return items


def reset() -> None:
    """重置客户端（切换传输 / 测试用）。"""
    global _CLIENT, _TRANSPORT_MODE
    _CLIENT = None
    _TRANSPORT_MODE = None