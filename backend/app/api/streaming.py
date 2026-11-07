"""把 `graph.stream(...)` 翻译成 SSE 文本（这一层只做翻译，不写业务）。

事件协议（前端只认这 6 种）：

    event: meta       {thread_id, user_id, tenant_id, roles}
    event: node       {node, ms, intent?, risk?, gate?, outcome?, ...}  每走完一个节点推进度
    event: token      {text}                                           answer 节点的模型输出
    event: interrupt  {thread_id, next, payloads, elapsed_ms}           图停下来了，等人
    event: done       {outcome, reply, citations, ticket_no, via, ...}  一条链路走完（outcome 为空=正常完成）
    event: error      {message}

为什么用 `stream_mode=["updates", "messages"]`：
- `updates`：每走完一个节点给一条，前端能显示"正在检索 / 正在规划"，也用来量节点耗时；
- `messages`：模型在节点里产生的 token 也会流出来（LangGraph 自带回调，不用改节点代码），
  我们只转发 `answer_with_citations` 与 `compose_reply` 的 token（分类节点输出的是 JSON，流给用户看没意义）。
"""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

# 只把"给人看"的节点 token 推给前端：回答节点 + 闲聊回复（compose_reply 只在闲聊时调模型）
TOKEN_NODES = {"answer_with_citations", "compose_reply"}

# 每走完一个节点，往前端推这几个"人看得懂"的字段（其余细节留在 State / 详情接口）
NODE_FIELDS = ("intent", "risk", "gate", "outcome", "via")


def sse(event: str, data: Any) -> str:
    """拼一个 SSE 事件（data 走 JSON，避免裸换行破坏协议）。"""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _text_of(message: Any) -> str:
    """从 LangChain 的 message chunk 里取文本（兼容 str 和 content block 两种）。"""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in {"text", "text_delta"}:
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return ""


def _usage_of(message: Any) -> tuple[int, int]:
    """取模型返回的 token 用量（DeepSeek 在流结束的那条 chunk 上带 usage_metadata）。"""
    usage = getattr(message, "usage_metadata", None)
    if not isinstance(usage, dict):
        return 0, 0
    return int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)


def _node_event(node: str, delta: Any, ms: int = 0) -> dict[str, Any]:
    """节点事件只带"值得展示"的字段，别把整个 state 推给前端。"""
    data: dict[str, Any] = {"node": node}
    if ms:
        data["ms"] = ms
    if isinstance(delta, dict):
        for key in NODE_FIELDS:
            value = delta.get(key)
            if value not in (None, "", [], {}):
                data[key] = value
        if isinstance(delta.get("policy_evidence"), list):
            data["evidence_count"] = len(delta["policy_evidence"])
        if isinstance(delta.get("facts"), list):
            data["facts_count"] = len(delta["facts"])
    return data


def _citations(state: dict[str, Any]) -> list[str]:
    """把检索到的资料整理成前端渲染引用卡片用的字符串。"""
    items = []
    for hit in state.get("policy_evidence") or []:
        citation = hit.get("citation") or hit.get("title") or ""
        if citation:
            items.append(str(citation))
    return items


def _ticket_no(state: dict[str, Any]) -> str | None:
    """单号从工具返回值现取（State 里不再存第二份）。"""
    result = state.get("result") or {}
    ticket = result.get("ticket") if isinstance(result.get("ticket"), dict) else {}
    return ticket.get("ticket_no") or result.get("ticket_no") or None


def _done_event(
    state: dict[str, Any], elapsed_ms: int, tokens: dict[str, int], thread_id: str
) -> dict[str, Any]:
    return {
        # thread_id 用参数兜底：老 checkpoint（initial_state 还没写这个字段时存的）里可能是空的，
        # 而前端要把 done 里的 thread_id 存起来继续 resume，不能给它 None。
        "thread_id": state.get("thread_id") or thread_id,
        "outcome": state.get("outcome"),
        "intent": state.get("intent"),
        "gate": state.get("gate"),
        "risk": state.get("risk"),
        "reply": state.get("reply"),
        "citations": _citations(state),
        "ticket_no": _ticket_no(state),
        "via": state.get("via"),
        "approval": state.get("approval"),
        "elapsed_ms": elapsed_ms,
        "tokens": tokens,
    }


def iter_sse(
    graph: Any,
    payload: Any,
    config: dict[str, Any],
    *,
    context: Any,
    thread_id: str,
    identity: dict[str, Any],
) -> Iterator[str]:
    """跑一次图，把过程翻译成 SSE 文本；结束后再读一次 checkpoint 判断"停没停"。"""
    started = time.perf_counter()
    last = started
    tokens_in = tokens_out = 0
    yield sse("meta", {"thread_id": thread_id, **identity})

    try:
        for mode, chunk in graph.stream(
            payload, config, context=context, stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                message, meta = chunk
                used_in, used_out = _usage_of(message)
                tokens_in += used_in
                tokens_out += used_out
                if (meta or {}).get("langgraph_node") in TOKEN_NODES:
                    text = _text_of(message)
                    if text:
                        yield sse("token", {"text": text})
                continue
            now = time.perf_counter()
            for node, delta in (chunk or {}).items():
                if node == "__interrupt__":
                    continue
                yield sse("node", _node_event(node, delta, int((now - last) * 1000)))
                last = now
    except Exception as exc:  # noqa: BLE001 - 上层只负责把错误告诉前端
        yield sse("error", {"message": f"{type(exc).__name__}: {exc}"})
        return

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    tokens = {"in": tokens_in, "out": tokens_out}
    snapshot = graph.get_state(config)
    interrupts = tuple(getattr(snapshot, "interrupts", ()) or ())
    if interrupts:
        yield sse(
            "interrupt",
            {
                "thread_id": thread_id,
                "next": list(snapshot.next or ()),
                "payloads": [getattr(item, "value", None) for item in interrupts],
                "elapsed_ms": elapsed_ms,
                "tokens": tokens,
            },
        )
        return
    yield sse("done", _done_event(dict(snapshot.values or {}), elapsed_ms, tokens, thread_id))
