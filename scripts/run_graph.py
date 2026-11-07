r"""CLI：不启动 FastAPI 也能在命令行把整张图走完（用于本地联调、断点恢复与状态检查）。

用法（在项目根目录、用 .venv 的 python）：

    python -m scripts.run_graph run    --thread t1 -m "发票怎么开"
    python -m scripts.run_graph run    --thread t2 -m "帮我建个工单：财务系统登录不上，影响 3 个人"
    python -m scripts.run_graph state  --thread t2
    python -m scripts.run_graph resume --thread t2 --approve
    python -m scripts.run_graph resume --thread t2 --edit urgency=high,title="财务系统登录失败"
    python -m scripts.run_graph resume --thread t2 --answer ticket_no=TK-20261031-0001
    python -m scripts.run_graph resume --thread t2 --reject -m "标题写错了"
    python -m scripts.run_graph chat   --thread t9
    python -m scripts.run_graph graph
    python -m scripts.run_graph tools
    python -m scripts.run_graph approvals --role approver          # 审批中心（谁申请、什么事、批没批）
    python -m scripts.run_graph approvals --status pending --role approver
    
跨进程恢复的关键：同一个 --thread 只影响 config.configurable.thread_id，
State 早就落在 Postgres（或兜底 SQLite）里了，进程退出不影响。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from backend.app.agents.graph import get_graph
from backend.app.agents.state import UserContext, initial_state

sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------------------------------- #
# 基础设施：上下文 / 配置 / 打印
# --------------------------------------------------------------------------- #
def _context(args) -> UserContext:
    roles = tuple(args.role or ["employee"])
    return UserContext(
        user_id=args.user,
        tenant_id=args.tenant,
        roles=roles,
        display_name=args.user,
    )


def _config(args) -> dict[str, Any]:
    return {"configurable": {"thread_id": args.thread}}


def _print_interrupt(payload: Any) -> None:
    data = dict(payload or {})
    kind = data.get("type")
    print("\n[暂停] 等你一句话" + (f"（类型：{kind}）" if kind else ""))
    if data.get("question"):
        print(f"  AI 问：{data['question']}")
    if data.get("title"):
        print(f"  标题：{data['title']}")
    if data.get("hint"):
        print(f"  提示：{data['hint']}")
    for field in data.get("fields") or []:
        source = field.get("source")
        print(f"  - {field.get('label')}: {field.get('value')}  [{source}]")
    if data.get("citations"):
        print("  引用：" + "、".join(str(x) for x in data["citations"] if x))
    print("  继续：python -m scripts.run_graph resume --thread <id> --approve / --reject / --edit k=v / --answer k=v")
    print("\n[原始载荷]")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _show_result(result: dict[str, Any]) -> None:
    print("\n[完成]")
    for key in ("outcome", "intent", "gate", "via"):
        if result.get(key):
            print(f"  {key:10s}: {result[key]}")
    if result.get("reply"):
        print("\n[回复]")
        print(result["reply"])
    evidence = result.get("policy_evidence") or []
    if evidence:
        print("\n[引用]")
        for item in evidence:
            print(f"  {item.get('citation')}  score={item.get('score')}")
    if result.get("error"):
        print(f"\n[错误] {result['error']}")


def _snapshot_summary(snapshot: Any) -> dict[str, Any]:
    values = dict(snapshot.values or {})
    return {
        "next": list(snapshot.next or ()),
        "outcome": values.get("outcome"),
        "intent": values.get("intent"),
        "gate": values.get("gate"),
        "risk": values.get("risk"),
        "reply": (values.get("reply") or "")[:120],
    }


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #
def _invoke(args, resume_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    graph = get_graph()
    config = _config(args)
    context = _context(args)
    if resume_payload is not None:
        from langgraph.types import Command

        return graph.invoke(Command(resume=resume_payload), config, context=context)
    state = initial_state(
        tenant_id=args.tenant, user_id=args.user, query=args.message, thread_id=args.thread
    )
    return graph.invoke(state, config, context=context)


def _handle_output(result: dict[str, Any]) -> None:
    interrupts = result.get("__interrupt__")
    if interrupts:
        _print_interrupt(interrupts[0].value)
        return
    _show_result(result)


def cmd_run(args) -> None:
    _handle_output(_invoke(args))


def _parse_pairs(raw: str | None) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value.lower() in {"true", "false"}:
            pairs[key.strip()] = value.lower() == "true"
        else:
            pairs[key.strip()] = value
    return pairs


def cmd_resume(args) -> None:
    payload: dict[str, Any]
    if args.answer:
        payload = {"answers": _parse_pairs(args.answer)}
    elif args.approve:
        payload = {"type": "decision", "decision": {"type": "approve"}}
    elif args.reject:
        payload = {"type": "decision", "decision": {"type": "reject", "message": args.message or "不同意"}}
    elif args.edit:
        payload = {"type": "decision", "decision": {"type": "edit", "patch": _parse_pairs(args.edit)}}
    else:
        payload = {"type": "decision", "decision": {"type": "approve"}}
    _handle_output(_invoke(args, payload))


def cmd_state(args) -> None:
    graph = get_graph()
    snapshot = graph.get_state(_config(args))
    print(json.dumps(_snapshot_summary(snapshot), ensure_ascii=False, indent=2, default=str))
    action = (snapshot.values or {}).get("action")
    if action:
        print("\n[action]")
        print(json.dumps(action, ensure_ascii=False, indent=2, default=str))


def cmd_graph(args) -> None:
    print(get_graph().get_graph().draw_mermaid())


def cmd_tools(args) -> None:
    from backend.app.agents.tools import mcp_client

    print(json.dumps(mcp_client.transport_info(), ensure_ascii=False, indent=2))
    catalog = mcp_client.tool_catalog()
    print(f"\n共 {len(catalog)} 个工具：")
    for item in catalog:
        print(f"  [{item['server']}] {item['name']:22s} {item['label']:8s} {item['risk']}")


def _actor(args) -> dict[str, Any]:
    """CLI 参数 → 身份票据（和节点里的 actor_of 同一个形状）。"""
    return {"user_id": args.user, "tenant_id": args.tenant, "roles": list(args.role or ["employee"])}


def cmd_approvals(args) -> None:
    from backend.app.agents.tools import ticket_tools

    data = ticket_tools.list_approvals(_actor(args), status=args.status or "", limit=args.limit)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_chat(args) -> None:
    print("输入问题，回车发送；:q 退出。")
    while True:
        try:
            line = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {":q", "quit", "exit"}:
            break
        args.message = line
        _handle_output(_invoke(args))


# --------------------------------------------------------------------------- #
# 参数
# --------------------------------------------------------------------------- #
def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--thread", default="t1", help="会话 id（= thread_id，跨进程恢复靠它）")
    parser.add_argument("--tenant", default="tenant-demo", help="租户 id（多租户隔离）")
    parser.add_argument("--user", default="u-1001", help="员工 id")
    parser.add_argument(
        "--role",
        action="append",
        choices=["employee", "approver", "kb_owner"],
        help="角色，可重复：--role employee --role kb_owner",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SmartDesk-Agent 服务台 Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="发一句话，跑到暂停或结束")
    _add_common(run)
    run.add_argument("-m", "--message", required=True, help="员工说的话")
    run.set_defaults(func=cmd_run)

    resume = sub.add_parser("resume", help="从暂停点继续（确认 / 审批 / 补充信息）")
    _add_common(resume)
    resume.add_argument("--approve", action="store_true", help="同意")
    resume.add_argument("--reject", action="store_true", help="驳回")
    resume.add_argument("--edit", help="改字段后继续，如 urgency=high,title=\"xxx\"")
    resume.add_argument("--answer", help="补充信息，如 ticket_no=TK-20261031-0001")
    resume.add_argument("-m", "--message", help="驳回理由")
    resume.set_defaults(func=cmd_resume)

    state = sub.add_parser("state", help="看当前 State 快照（停在哪个节点、有哪些字段）")
    _add_common(state)
    state.set_defaults(func=cmd_state)

    graph = sub.add_parser("graph", help="打印 Mermaid 图")
    _add_common(graph)
    graph.set_defaults(func=cmd_graph)

    tools = sub.add_parser("tools", help="列 MCP 工具与传输方式")
    _add_common(tools)
    tools.set_defaults(func=cmd_tools)

    chat = sub.add_parser("chat", help="交互式聊天")
    _add_common(chat)
    chat.set_defaults(func=cmd_chat)

    approvals = sub.add_parser("approvals", help="审批中心：列审批留痕（pending / approved / rejected）")
    _add_common(approvals)
    approvals.add_argument(
        "--status",
        default="",
        choices=["", "pending", "approved", "edited", "rejected", "rejected_permission"],
        help="只看某个状态",
    )
    approvals.add_argument("--limit", type=int, default=20)
    approvals.set_defaults(func=cmd_approvals)


    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

