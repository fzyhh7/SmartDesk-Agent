"""取证据（gather_evidence）：主图第 3 个节点，一次调用里做两件事。

为什么要这个节点（面试常问）：
- 回答"怎么办"需要公司制度（policy_evidence），回答"到哪一步了"需要业务事实（facts）；
- 两者都是"动手/开口之前必须先看清的东西"，所以放同一个节点，先取制度再取事实。

"提到了哪张单"是独立于 intent/op 的一条轴：问制度时也可能提到单号
（"TK-… 按规定能不能延期"）。这条轴**由模型判断**（`classification.reference` 枚举：
none / number / my_last / my_recent），代码只做两件事：单号必须正则校验通过才采信、
指代类型翻译成查几张。**这里不读 `op`**——op 是 `plan_action`（本节点之后）才有的字段。

本节点遵循单一职责原则：只负责检索制度与查询只读事实，不生成自然语言回复。
"""

from __future__ import annotations

import logging
from typing import Any

from .. import knowledge
from langgraph.runtime import Runtime

from ..state import TicketState, UserContext, actor_of
from ..tools import ticket_tools
from .plan_action import find_ticket_no

logger = logging.getLogger(__name__)

TOP_K = 3

# 动作型检索用的"主题词"：把口语化请求翻成知识库里可能出现的说法
ACTION_TOPICS: dict[str, str] = {
    "create_ticket": "工单 建单 提交流程 响应时间 优先级",
    "update_ticket": "工单 修改 变更 处理时限",
    "close_ticket": "工单 关闭 结案 通知 回访",
    "publish_kb_article": "知识库 发布 文章 审核规范",
    "query_ticket": "工单 查询 单号 状态",
    "list_tickets": "工单 列表 我的工单 未结单",
}

# "提到了哪张单"由模型判断（classification.reference），这里只做两件事：
# 单号必须能正则校验通过才采信（防模型编造），指代类型翻译成"查几张"。
LAST_ONE = 1
RECENT_MANY = 5


def _policy_query(state: TicketState) -> str:
    """知识型用员工原话；动作型用「主题词 + 动作」，避免把'帮我建个工单：财务系统登录不上'
    拿去检索出考勤/限流这类不相关制度。"""
    if state.get("intent") != "action":
        return state.get("query", "")
    action = state.get("action") or {}
    topic = ACTION_TOPICS.get(action.get("op", ""), "")
    return f"{topic} {state.get('query', '')}".strip()


def retrieve_policy(state: TicketState) -> list[dict[str, Any]]:
    """查公司制度：Milvus 双路召回 + RRF 粗排 → Cross-Encoder 精排 → policy_evidence（带引用）。"""
    try:
        hits = knowledge.search(_policy_query(state), k=TOP_K, tenant_id=state.get("tenant_id"))
    except knowledge.MilvusUnavailable as exc:
        logger.warning("知识库不可用，跳过制度检索：%s", exc)
        return []
    evidence: list[dict[str, Any]] = []
    for index, hit in enumerate(hits, start=1):
        evidence.append(
            {
                "idx": index,
                "doc_id": hit["doc_id"],
                "title": hit["title"],
                # chapter = 第 X 章，section = X.Y 节（引用串里两层都带）
                "chapter": hit.get("h2", ""),
                "section": hit.get("h3") or hit.get("h2") or "",
                "source_file": hit.get("source_file", ""),
                "score": hit["score"],
                "snippet": (hit.get("content") or "")[:180],
                "citation": f"[{index}] {hit.get('citation') or hit['title']}",
            }
        )
    return evidence


def _where_ticket(state: TicketState) -> tuple[str, str]:
    """这句话提到了哪张单：返回 (指代类型, 单号)。

    指代类型听模型的（`classification.reference`），单号只认正则校验通过的值——
    这样"上次那个卡了半天的报修"也能查，而模型编出来的单号会被丢掉。
    """
    classification = state.get("classification") or {}
    kind = str(classification.get("reference") or "none")
    hint = str(classification.get("reference_hint") or "")
    ticket_no = find_ticket_no(hint) or find_ticket_no(state.get("query", ""))
    if ticket_no:
        return "number", ticket_no
    return (kind if kind in {"my_last", "my_recent"} else "none"), ""


def read_ticket_facts(state: TicketState, actor: dict[str, Any]) -> list[dict[str, Any]]:
    """查业务事实：只读工具（不写库、不改状态）。权限由 MCP server 按 actor 判定。

    三路：有单号 → 查这一张；"我的上一张" → 最近 1 张；"我的那些" → 最近 5 张。
    """
    args = (state.get("action") or {}).get("args") or {}

    kind, ticket_no = _where_ticket(state)
    ticket_no = args.get("ticket_no") or ticket_no
    if ticket_no:
        result = ticket_tools.query_ticket(actor, ticket_no) or {}
        ticket = result.get("ticket")
        if ticket:
            return [ticket]
        # 查不到/没权限也要留一条事实：下游据此"直接拒绝"，而不是继续问参数或进审批队列
        error = result.get("error") if isinstance(result.get("error"), dict) else {}
        if error:
            return [
                {
                    "ticket_no": ticket_no,
                    "can_write": False,
                    "denied_reason": error.get("reason") or error.get("code") or "",
                }
            ]
        return []

    # 指代消解：不问单号也能查，把"可解析的指代"和"真的缺参数"分开，
    # plan_action 就不会拿"我的上一张"去反问了。
    limit = {"my_last": LAST_ONE, "my_recent": RECENT_MANY}.get(kind, 0)
    if limit:
        result = ticket_tools.list_tickets(actor, limit=limit)
        return result.get("tickets") or []
    return []


def gather_evidence(state: TicketState, runtime: Runtime[UserContext]) -> dict[str, Any]:
    """节点入口：制度 + 事实一起取，返回结构化字段（不写自然语言）。"""
    actor = actor_of(runtime)
    policy_evidence = retrieve_policy(state)
    facts = read_ticket_facts(state, actor)
    return {"policy_evidence": policy_evidence, "facts": facts}