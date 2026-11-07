"""kb-server：知识库域的 MCP 服务（2 个业务工具：1 读 + 1 写，外加 health 检查）。

设计要点：
- 与 ticket-server 一起由 MultiServerMCPClient 统一装配管理，按业务域解耦工具服务
- 写入 Milvus 时只传 dense 稠密向量，sparse 稀疏向量由服务端内置 BM25 函数自动生成
- search_kb 既可供外部 MCP 客户端调用，也可作为独立工具复用

鉴权（零信任原则）：同样要求传入 `actor` 身份票据，租户从 actor 取；发布知识只有 kb_owner 能做，
即使 Agent 的审批节点被绕过，工具层也会拦截拒绝。

工具清单（7 个里的 2 个）：
- search_kb(actor, query, top_k)                        读
- publish_kb_article(actor, title, content, ...)        写，不可逆/全员可见 → 审批门

两个工具的定位略有不同：
- `publish_kb_article` 是**图内**会走到的（classify 出 op → plan_action 判风险 → 审批 → execute 调它）。
- `search_kb` 给**外部 MCP 客户端 / 其它 Agent 复用**（演示 Agentic RAG 的"工具化检索"）；
  主图的 `gather_evidence` 为了省一次子进程 IPC 直连 `knowledge.search`，走的是同一个 Milvus collection。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.mcp.servers import guard  # noqa: E402

kb_mcp = FastMCP(
    "smartdesk-kb",
    instructions="企业知识库服务：检索已发布文章、发布新文章（发布后全员可见且不可撤回，需要 kb_owner 审批）。",
)


def _store():
    """延迟导入：函数体内的 import 不会在模块加载时就建 Milvus 连接。"""
    from backend.app.agents.rag import vector_store

    return vector_store


def _warmup() -> None:
    """stdio 子进程启动时，在主线程里先把重依赖导入一遍。

    为什么需要这一步：FastMCP 把**同步工具**丢进 anyio 的 worker 线程执行，
    而 numpy / pymilvus 这一串 C 扩展在该 worker 线程里首次 import 会卡住
    （实测 `health` 调用等 90s 仍不返回，栈停在 `numpy/_core/_multiarray_umath`；
    同一个 import 放在主线程或普通线程里只要 1s 左右）。
    主线程预热一次约 1 秒，之后工具调用即时返回。

    注意这里只 import 模块，**不会**连 Milvus——`get_client()` 仍然是懒连接。
    """
    _store()


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@kb_mcp.tool()
def search_kb(actor: dict[str, Any], query: str, top_k: int = 3) -> str:
    """在知识库里做混合检索（dense + BM25 + RRF 粗排 → Cross-Encoder 精排），只返回已发布文章（只读）。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    query = (query or "").strip()
    if not query:
        return guard.deny("invalid_argument", "query 不能为空")
    try:
        hits = _store().hybrid_search(
            query,
            k=max(1, min(int(top_k or 3), 10)),
            tenant_id=actor_data["tenant_id"],
        )
    except Exception as exc:
        return guard.deny("unavailable", f"知识库不可用：{exc}")
    channel = hits[0].get("channel", "hybrid") if hits else "hybrid"
    return _to_json({"ok": True, "count": len(hits), "hits": hits, "channel": channel})


@kb_mcp.tool()
def publish_kb_article(
    actor: dict[str, Any],
    title: str,
    content: str,
    tags: list[str] | None = None,
    change_note: str = "",
) -> str:
    """发布知识文章（写操作；发布后全员可见、不可撤回，需要 kb_owner 审批）。"""
    actor_data, denied = guard.require_actor(actor)
    if denied:
        return denied
    if not guard.can_publish_kb(actor_data):
        return guard.deny(
            "forbidden",
            "只有知识库 owner 及以上角色可以发布/修改知识文章（发布后全员可见、撤不回）",
            actor={"user_id": actor_data["user_id"], "roles": list(actor_data["roles"])},
        )
    title = (title or "").strip()
    content = (content or "").strip()
    if not title:
        return guard.deny("invalid_argument", "title 不能为空")
    if not content:
        return guard.deny("invalid_argument", "content 不能为空")
    try:
        result = _store().publish_article(
            title=title,
            content=content,
            tags=tags or [],
            change_note=change_note,
            tenant_id=actor_data["tenant_id"],
        )
    except Exception as exc:
        return guard.deny("unavailable", f"写入知识库失败：{exc}")
    return _to_json({"ok": True, **result})


@kb_mcp.tool()
def health() -> str:
    """服务健康检查（只读，不需要身份）。"""
    try:
        stats = _store().collection_stats()
        return _to_json({"ok": True, "server": "kb", **stats})
    except Exception as exc:
        return _to_json({"ok": False, "server": "kb", "error": str(exc)})


if __name__ == "__main__":
    _warmup()
    kb_mcp.run(transport="stdio", show_banner=False)
