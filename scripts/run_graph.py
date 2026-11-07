r"""CLI锛氫笉鍚姩 FastAPI 涔熻兘鍦ㄥ懡浠よ鎶婃暣寮犲浘璧板畬锛堢敤浜庢湰鍦拌仈璋冦€佹柇鐐规仮澶嶄笌鐘舵€佹鏌ワ級銆?
鐢ㄦ硶锛堝湪椤圭洰鏍圭洰褰曘€佺敤 .venv 鐨?python锛夛細

    python -m scripts.run_graph run    --thread t1 -m "鍙戠エ鎬庝箞寮€"
    python -m scripts.run_graph run    --thread t2 -m "甯垜寤轰釜宸ュ崟锛氳储鍔＄郴缁熺櫥褰曚笉涓婏紝褰卞搷 3 涓汉"
    python -m scripts.run_graph state  --thread t2
    python -m scripts.run_graph resume --thread t2 --approve
    python -m scripts.run_graph resume --thread t2 --edit urgency=high,title="璐㈠姟绯荤粺鐧诲綍澶辫触"
    python -m scripts.run_graph resume --thread t2 --answer ticket_no=TK-20261031-0001
    python -m scripts.run_graph resume --thread t2 --reject -m "鏍囬鍐欓敊浜?
    python -m scripts.run_graph chat   --thread t9
    python -m scripts.run_graph graph
    python -m scripts.run_graph tools
    python -m scripts.run_graph approvals --role approver          # 瀹℃壒涓績锛堣皝鐢宠銆佷粈涔堜簨銆佹壒娌℃壒锛?    python -m scripts.run_graph approvals --status pending --role approver
    
璺ㄨ繘绋嬫仮澶嶇殑鍏抽敭锛氬悓涓€涓?--thread 鍙奖鍝?config.configurable.thread_id锛?State 鏃╁氨钀藉湪 Postgres锛堟垨鍏滃簳 SQLite锛夐噷浜嗭紝杩涚▼閫€鍑轰笉褰卞搷銆?"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from backend.app.agents.graph import get_graph
from backend.app.agents.state import UserContext, initial_state

sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------------------------------- #
# 鍩虹璁炬柦锛氫笂涓嬫枃 / 閰嶇疆 / 鎵撳嵃
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
    print("\n[鏆傚仠] 绛変綘涓€鍙ヨ瘽" + (f"锛堢被鍨嬶細{kind}锛? if kind else ""))
    if data.get("question"):
        print(f"  AI 闂細{data['question']}")
    if data.get("title"):
        print(f"  鏍囬锛歿data['title']}")
    if data.get("hint"):
        print(f"  鎻愮ず锛歿data['hint']}")
    for field in data.get("fields") or []:
        source = field.get("source")
        print(f"  - {field.get('label')}: {field.get('value')}  [{source}]")
    if data.get("citations"):
        print("  寮曠敤锛? + "銆?.join(str(x) for x in data["citations"] if x))
    print("  缁х画锛歱ython -m scripts.run_graph resume --thread <id> --approve / --reject / --edit k=v / --answer k=v")
    print("\n[鍘熷杞借嵎]")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _show_result(result: dict[str, Any]) -> None:
    print("\n[瀹屾垚]")
    for key in ("outcome", "intent", "gate", "via"):
        if result.get(key):
            print(f"  {key:10s}: {result[key]}")
    if result.get("reply"):
        print("\n[鍥炲]")
        print(result["reply"])
    evidence = result.get("policy_evidence") or []
    if evidence:
        print("\n[寮曠敤]")
        for item in evidence:
            print(f"  {item.get('citation')}  score={item.get('score')}")
    if result.get("error"):
        print(f"\n[閿欒] {result['error']}")


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
# 瀛愬懡浠?# --------------------------------------------------------------------------- #
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
        payload = {"type": "decision", "decision": {"type": "reject", "message": args.message or "涓嶅悓鎰?}}
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
    print(f"\n鍏?{len(catalog)} 涓伐鍏凤細")
    for item in catalog:
        print(f"  [{item['server']}] {item['name']:22s} {item['label']:8s} {item['risk']}")


def _actor(args) -> dict[str, Any]:
    """CLI 鍙傛暟 鈫?韬唤绁ㄦ嵁锛堝拰鑺傜偣閲岀殑 actor_of 鍚屼竴涓舰鐘讹級銆?""
    return {"user_id": args.user, "tenant_id": args.tenant, "roles": list(args.role or ["employee"])}


def cmd_approvals(args) -> None:
    from backend.app.agents.tools import ticket_tools

    data = ticket_tools.list_approvals(_actor(args), status=args.status or "", limit=args.limit)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_chat(args) -> None:
    print("杈撳叆闂锛屽洖杞﹀彂閫侊紱:q 閫€鍑恒€?)
    while True:
        try:
            line = input("\n浣? ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {":q", "quit", "exit"}:
            break
        args.message = line
        _handle_output(_invoke(args))


# --------------------------------------------------------------------------- #
# 鍙傛暟
# --------------------------------------------------------------------------- #
def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--thread", default="t1", help="浼氳瘽 id锛? thread_id锛岃法杩涚▼鎭㈠闈犲畠锛?)
    parser.add_argument("--tenant", default="tenant-demo", help="绉熸埛 id锛堝绉熸埛闅旂锛?)
    parser.add_argument("--user", default="u-1001", help="鍛樺伐 id")
    parser.add_argument(
        "--role",
        action="append",
        choices=["employee", "approver", "kb_owner"],
        help="瑙掕壊锛屽彲閲嶅锛?-role employee --role kb_owner",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SmartDesk-Agent 鏈嶅姟鍙?Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="鍙戜竴鍙ヨ瘽锛岃窇鍒版殏鍋滄垨缁撴潫")
    _add_common(run)
    run.add_argument("-m", "--message", required=True, help="鍛樺伐璇寸殑璇?)
    run.set_defaults(func=cmd_run)

    resume = sub.add_parser("resume", help="浠庢殏鍋滅偣缁х画锛堢‘璁?/ 瀹℃壒 / 琛ュ厖淇℃伅锛?)
    _add_common(resume)
    resume.add_argument("--approve", action="store_true", help="鍚屾剰")
    resume.add_argument("--reject", action="store_true", help="椹冲洖")
    resume.add_argument("--edit", help="鏀瑰瓧娈靛悗缁х画锛屽 urgency=high,title=\"xxx\"")
    resume.add_argument("--answer", help="琛ュ厖淇℃伅锛屽 ticket_no=TK-20261031-0001")
    resume.add_argument("-m", "--message", help="椹冲洖鐞嗙敱")
    resume.set_defaults(func=cmd_resume)

    state = sub.add_parser("state", help="鐪嬪綋鍓?State 蹇収锛堝仠鍦ㄥ摢涓妭鐐广€佹湁鍝簺瀛楁锛?)
    _add_common(state)
    state.set_defaults(func=cmd_state)

    graph = sub.add_parser("graph", help="鎵撳嵃 Mermaid 鍥?)
    _add_common(graph)
    graph.set_defaults(func=cmd_graph)

    tools = sub.add_parser("tools", help="鍒?MCP 宸ュ叿涓庝紶杈撴柟寮?)
    _add_common(tools)
    tools.set_defaults(func=cmd_tools)

    chat = sub.add_parser("chat", help="浜や簰寮忚亰澶?)
    _add_common(chat)
    chat.set_defaults(func=cmd_chat)

    approvals = sub.add_parser("approvals", help="瀹℃壒涓績锛氬垪瀹℃壒鐣欑棔锛坧ending / approved / rejected锛?)
    _add_common(approvals)
    approvals.add_argument(
        "--status",
        default="",
        choices=["", "pending", "approved", "edited", "rejected", "rejected_permission"],
        help="鍙湅鏌愪釜鐘舵€?,
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
