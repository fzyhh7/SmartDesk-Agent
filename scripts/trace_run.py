"""逐节点跟读工具：跑一条请求，把每个节点「写了哪些字段」一个个打出来。

用法：
    python -m scripts.trace_run -m "发票怎么开"
    python -m scripts.trace_run -m "帮我建个工单：VPN 连不上，影响 2 个人"
    python -m scripts.trace_run -m "..." --resume '{"type":"decision","decision":"approve"}'

它比 run 子命令多做的唯一一件事：用 stream_mode="updates" 看「每一步谁写了什么」，
而不是只看最后结果。这是读代码时最需要的视角。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from backend.app.agents.graph import get_graph
from backend.app.agents.state import UserContext, initial_state


MAX = 88


def _short(value: Any) -> str:
    if isinstance(value, str):
        text = value.replace("\n", "\\n")
        return text if len(text) <= MAX else text[:MAX] + "…"
    if isinstance(value, list):
        if not value:
            return "[]"
        head = value[0]
        if isinstance(head, dict):
            keys = "/".join(list(head.keys())[:5])
            return f"[{len(value)} 条, 每条形如 {{{keys}}}]"
        return f"[{len(value)} 条] " + _short(str(head))
    if isinstance(value, dict):
        keys = list(value.keys())
        return "{" + ", ".join(keys[:6]) + ("…" if len(keys) > 6 else "") + "}"
    return str(value)


def _print_update(node: str, update: Any, seen: dict[str, Any]) -> None:
    print(f"\n{'=' * 78}\n▶ 节点 {node}")
    if not isinstance(update, dict):
        print(f"   返回：{_short(update)}")
        return
    changed = 0
    for key, value in update.items():
        if key == "messages":
            print(f"   messages      +{len(value)} 条（由 add_messages reducer 追加）")
            for msg in value:
                kind = type(msg).__name__
                print(f"                 · {kind}: {_short(getattr(msg, 'content', ''))}")
            changed += 1
            continue
        same = key in seen and seen[key] == value
        seen[key] = value
        if same:
            continue
        changed += 1
        print(f"   {key:<16} {_short(value)}")
    if not changed:
        print("   （这个节点没有改动任何字段）")
    else:
        print(f"   —— 本节点写了 {changed} 个字段，其余 {len(seen) - changed} 个沿用上一步")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="逐节点跟读一条请求")
    parser.add_argument("-m", "--message", required=True, help="用户这一句话")
    parser.add_argument("--thread", default="trace", help="thread_id，同一 id 才能接着跑")
    parser.add_argument("--tenant", default="tenant-demo")
    parser.add_argument("--user", default="u-1001")
    parser.add_argument("--role", action="append", default=None, help="可重复，如 --role approver")
    parser.add_argument("--resume", default=None, help="JSON 字符串：从上一个 interrupt 继续")
    args = parser.parse_args(argv)

    graph = get_graph()
    config = {"configurable": {"thread_id": args.thread}}
    context = UserContext(
        tenant_id=args.tenant,
        user_id=args.user,
        roles=tuple(args.role or ["employee"]),
    )

    seen: dict[str, Any] = {}
    payload: Any = initial_state(
        tenant_id=args.tenant, user_id=args.user, query=args.message, thread_id=args.thread
    )
    if isinstance(payload, dict):
        seen.update(payload)   # 起点已有的字段不算"本节点写的"
    if args.resume:
        from langgraph.types import Command

        payload = Command(resume=json.loads(args.resume))
        print(f"[跟读] 线程 {args.thread}｜从暂停点继续（Command(resume=...)）")
    else:
        print(f"[跟读] 线程 {args.thread}｜起点：{args.message!r}")

    for chunk in graph.stream(payload, config, context=context, stream_mode="updates"):
        if "__interrupt__" in chunk:
            interrupts = chunk["__interrupt__"]
            value = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
            print(f"\n{'=' * 78}\n⏸ 图在 interrupt 处停下（进程可以退出，State 已落 checkpoint）")
            print(json.dumps(value, ensure_ascii=False, indent=2)[:1600])
            print(f"\n继续：python -m scripts.trace_run --thread {args.thread} -m \"同一条输入\" \\")
            print("        --resume '{\"type\":\"decision\",\"decision\":\"approve\"}'")
            return 0
        for node, update in chunk.items():
            _print_update(node, update, seen)

    snapshot = graph.get_state(config)
    print(f"\n{'=' * 78}\n■ 跑完｜next={snapshot.next}｜outcome={snapshot.values.get('outcome')}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())