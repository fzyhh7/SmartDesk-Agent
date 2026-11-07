"""plan_action 节点：把"员工想要什么"拆成"工具参数 + 风险等级 + 走哪个闸门"。

设计要点：
- Context 只读（谁/租户/角色），State 可变（草稿、闸门、决策）
- 复用 classify 阶段的意图摘要，并结合确定性规则/正则提取工单号与变更字段，防止模型幻觉编造单号
- 节点只负责计算数据并返回字段，具体路由跳转由 graph.py 的条件边统一决定

三条铁律：
1. 参数只能来自"员工说的 + 知识库规定的 + 登录态"，模型推断的字段必须标记 agent_inferred 并要求确认
2. 缺必需参数不许猜，进 clarify 门反问
3. 闸门只看风险等级：只读直通、可撤销走确认、不可逆/全员可见走审批
"""

from __future__ import annotations

import logging
import re
from typing import Any


from langgraph.runtime import Runtime

from ..state import TicketState, UserContext
from .action_spec import FIELD_LABELS, GATE_BY_RISK, RISK_BY_OP, compute_risk, server_of

logger = logging.getLogger(__name__)

TICKET_NO_PATTERN = re.compile(r"TK-\d{8}-\d{4}", re.IGNORECASE)

QUOTED_PATTERN = re.compile(r"[「“\"]([^」”\"]{2,40})[」”\"]")


def extract_quoted_text(text: str) -> str:
    """员工用「」/引号写的标题优先当标题。"""
    match = QUOTED_PATTERN.search(text)
    return match.group(1).strip() if match else ""


def find_ticket_no(text: str) -> str | None:
    match = TICKET_NO_PATTERN.search(text)
    return match.group(0).upper() if match else None


NOTIFY_CLAUSE_PATTERN = re.compile(
    r"[，,、]?\s*(顺便|并且|然后|同时)?\s*(通知|告知|知会)(一下)?\s*(提单人|提报人|提交人|对方|他|她)?\s*$"
)


def _extract_resolution(query: str) -> str:
    text = NOTIFY_CLAUSE_PATTERN.sub("", query)
    text = re.sub(r"(把|将)?(工单)?\s*TK-\d{8}-\d{4}\s*(关闭|关掉|结了|结掉)", "", text)
    text = re.sub(r"^(帮我|麻烦|请|帮忙)", "", text)
    text = re.sub(r"(把|将)?[^，。,.!！]{0,8}(工单)?[^，。,.!！]{0,6}(关掉|关闭|结了|结掉)", "", text)
    text = text.strip("，。,.!！ ")
    # 员工只说"把那些单关掉"时，剩下的碎片（"把我工"）不能当解决说明写进工单
    return text if len(text) >= 4 else "员工反馈问题已解决，确认关闭"


def _extract_patch(query: str) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if "紧急" in query or "高优" in query or "最高" in query:
        patch["urgency"] = "high"
    elif "低优" in query or "不急" in query:
        patch["urgency"] = "low"
    elif "中优" in query:
        patch["urgency"] = "medium"
    if "关闭" in query or "关掉" in query:
        patch["status"] = "closed"
    elif "处理中" in query or "接了" in query:
        patch["status"] = "in_progress"
    elif "重新打开" in query or "重开" in query:
        patch["status"] = "open"
    return patch


def _kb_content(state: TicketState) -> str:
    """发布知识文章的正文：只认员工自己给的引号内容，不拿检索片段硬凑。

    为什么：检索到的政策片段可能是别的主题，拼进正文等于编造内容。
    员工没给正文时留空，让 clarify 节点去问一句"正文写什么"。
    """
    quoted = extract_quoted_text(state.get("query") or "")
    return quoted if len(quoted) >= 15 else ""


def _build_action(state: TicketState) -> tuple[dict[str, Any], list[str], dict[str, str], str]:
    """返回 (args, missing, arg_sources, 动作中文名)。"""
    action = state.get("action") or {}
    op = action.get("op") or ""
    query = state.get("query") or ""
    tenant_id = state.get("tenant_id") or ""
    user_id = state.get("user_id") or ""
    classification = state.get("classification") or {}
    summary = _clean_summary(classification.get("summary") or query[:40])
    urgency = classification.get("urgency") or "medium"
    topic = classification.get("topic") or "其他"

    if op == "create_ticket":
        args = {
            "title": summary,
            "description": query,
            "urgency": urgency,
            "category": topic,
            "reporter": user_id,
        }
        sources = {
            "title": "agent_inferred",
            "description": "from_user",
            "urgency": "agent_inferred",
            "category": "agent_inferred",
            "reporter": "from_context",
        }
        missing = [] if summary else ["title"]
        return args, missing, sources, "建工单"

    if op == "update_ticket":
        ticket_no = find_ticket_no(query) or ""
        patch = _extract_patch(query)
        sources = {"ticket_no": "from_user" if ticket_no else "agent_inferred", "patch": "agent_inferred"}
        missing = []
        if not ticket_no:
            missing.append("ticket_no")
        if not patch:
            missing.append("patch")
        return {"ticket_no": ticket_no, "patch": patch}, missing, sources, "改工单"

    if op == "close_ticket":
        ticket_no = find_ticket_no(query) or ""
        notify = any(word in query for word in ("通知", "告诉他", "告诉提单人", "发个消息"))
        args = {
            "ticket_no": ticket_no,
            "resolution": _extract_resolution(query),
            "notify_reporter": notify,
        }
        sources = {
            "ticket_no": "from_user" if ticket_no else "agent_inferred",
            "resolution": "from_user",
            "notify_reporter": "from_user",
        }
        missing = [] if ticket_no else ["ticket_no"]
        return args, missing, sources, "关工单"

    if op == "publish_kb_article":
        title = extract_quoted_text(query) or (summary if summary and summary != query else (topic + "常见问题"))
        args = {
            "title": title,
            "content": _kb_content(state),
            "tags": [topic, "员工提问沉淀"],
            "change_note": f"由员工提问整理：{query[:60]}",
        }
        sources = {
            "title": "agent_inferred",
            "content": "from_policy",
            "tags": "agent_inferred",
            "change_note": "from_context",
        }
        missing = [] if args["content"].strip() else ["content"]
        return args, missing, sources, "发布知识文章"

    if op == "query_ticket":
        ticket_no = find_ticket_no(query) or ""
        missing = [] if ticket_no else ["ticket_no"]
        return {"ticket_no": ticket_no}, missing, {"ticket_no": "from_user"}, "查工单"

    if op == "list_tickets":
        return (
            {"tenant_id": tenant_id, "status": "", "limit": 10},
            [],
            {"tenant_id": "from_context", "limit": "from_context"},
            "列工单",
        )

    return {}, ["op"], {}, "未知动作"


_SUMMARY_PREFIX_PATTERN = re.compile(
    r"^\s*(?:员工要求|员工申请|帮我|请|麻烦)?\s*"
    r"(?:建|开|提|报|登记|发|关|改|查)?个?(?:工单|单|知识库|文章)?\s*[:：]?\s*"
)


def _clean_summary(text: str) -> str:
    """LLM 常把"建工单："这种动作词带进标题，这里去掉，避免确认卡出现嵌套前缀。"""
    cleaned = _SUMMARY_PREFIX_PATTERN.sub("", text or "").strip()
    return cleaned or (text or "").strip()


def not_allowed(state: TicketState, roles: tuple[str, ...]) -> str | None:
    """对象级资格：这个人根本不该做这件事时，直接回一句并结束（不进闸门、不进待办）。

    规则本身在 server 的 guard；这里只读 `query_ticket` 带回来的 `can_write` / `denied_reason`。
    """
    action = state.get("action") or {}
    op = str(action.get("op") or "")
    if op == "publish_kb_article":
        if "kb_owner" not in roles:
            return "发布知识库需要 kb_owner 身份，当前身份（" + "、".join(roles) + "）不能发布。"
        return None
    if op in {"update_ticket", "close_ticket", "query_ticket"}:
        ticket_no = str((action.get("args") or {}).get("ticket_no") or "")
        record = _fact_for(state.get("facts") or [], ticket_no)
        if record and record.get("can_write") is False:
            verb = "查看" if op == "query_ticket" else "处理"
            return str(
                record.get("denied_reason")
                or f"你无权{verb}工单 {ticket_no}：只有提单人本人或主管能处理。"
            )
    return None


def _fact_for(facts: list[dict[str, Any]], ticket_no: str) -> dict[str, Any] | None:
    """从事实里挑出这张单（证据层已经把权限提示 can_write / notify_reports_self 附上了）。"""
    for record in facts or []:
        if str(record.get("ticket_no") or "") == ticket_no:
            return record
    return None


def plan_action(state: TicketState, runtime: Runtime[UserContext]) -> dict[str, Any]:
    """组装动作参数（不写库），按风险选闸门。"""
    action = state.get("action") or {}
    op = action.get("op") or ""
    # server 由 op 查表推导（不交给模型判断，少一个可能填错的字段）
    server = server_of(op)
    base_risk = RISK_BY_OP.get(op, "write_reversible")

    args, missing, arg_sources, label = _build_action(state)

    # clarify 里员工补过的字段要生效：用 action.args 覆盖默认推断值，再重算缺口
    for key, value in (action.get("args") or {}).items():
        if value not in (None, "", [], {}):
            args[key] = value
            arg_sources[key] = "from_user"
    missing = [name for name in missing if args.get(name) in (None, "", [], {})]

    # 证据层已经按"我的上一张 / 那些单"把单号解析出来了，就别再反问用户要单号：
    # 唯一命中一张才敢自动填，多张仍然要问（不能替员工猜是哪张）。
    facts = state.get("facts") or []
    reference = str((state.get("classification") or {}).get("reference") or "none")
    if "ticket_no" in missing and len(facts) == 1 and facts[0].get("ticket_no"):
        args["ticket_no"] = facts[0]["ticket_no"]
        arg_sources["ticket_no"] = "from_evidence"
        missing = [name for name in missing if name != "ticket_no"]

    # "通知提单人"而提单人就是操作者自己 → 没有通知对象，等价于不通知（风险也就不该升级）
    if args.get("notify_reporter"):
        record = _fact_for(facts, str(args.get("ticket_no") or ""))
        if record and record.get("notify_reports_self"):
            args["notify_reporter"] = False
            arg_sources["notify_reporter"] = "from_context"

    risk = compute_risk(op, args, base_risk)
    gate = "clarify" if missing else GATE_BY_RISK.get(risk, "confirm")

    # 动作只有一个真身：args 就是定稿参数（确认卡上改完会直接写回这里）
    action_out = {
        **action,
        "server": server,
        "op": op,
        "label": label,
        "args": args,
        "missing": missing,
        "sources": arg_sources,
    }

    # 员工说的是"我的上一张 / 那些单"，但名下确实一张都没有：
    # 这不是"缺参数"，再反问"你要查哪张单"只会让人莫名其妙，直接告诉他事实。
    if "ticket_no" in missing and reference in {"my_last", "my_recent"} and not facts:
        return {
            "action": action_out,
            "risk": risk,
            "gate": gate,
            "outcome": "not_found",
            "reply": (
                "你名下还没有工单，所以没有“上一张”可查。"
                "如果你是替别人问，把单号（形如 TK-20261106-0001）发我，我再查一次。"
            ),
        }

    # 对象级资格不通过：直接结束，不弹卡、不排队（"越权"不是"待审批"）
    denied = not_allowed({**state, "action": action_out}, tuple(runtime.context.roles))
    if denied:
        return {"action": action_out, "risk": risk, "gate": gate, "outcome": "denied", "reply": denied}

    update: dict[str, Any] = {"action": action_out, "risk": risk, "gate": gate}
    if missing:
        update["reply"] = f"还差 {', '.join(missing)}，我先问你一句。"
    return update