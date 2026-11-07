"""知识库工具（知识库 server 的语义封装）。`actor` 同 ticket_tools：只由节点从 Context 构造。"""

from __future__ import annotations

from typing import Any

from .mcp_client import call_tool

SERVER = "kb"


def search_kb(actor: dict[str, Any], query: str, *, top_k: int = 3) -> dict[str, Any]:
    return call_tool(SERVER, "search_kb", {"actor": actor, "query": query, "top_k": top_k})


def publish_kb_article(
    actor: dict[str, Any],
    *,
    title: str,
    content: str,
    tags: list[str] | None = None,
    change_note: str = "",
) -> dict[str, Any]:
    return call_tool(
        SERVER,
        "publish_kb_article",
        {
            "actor": actor,
            "title": title,
            "content": content,
            "tags": tags or [],
            "change_note": change_note,
        },
    )
