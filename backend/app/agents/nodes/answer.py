"""answer 节点：只负责"带出处的回答"，不做任何动作。

设计要点：
- 基于前置 `gather_evidence` 节点检索到的制度片段（`policy_evidence`）与工单事实（`facts`）生成回答
- 要求模型对制度结论强制标注 `[1][2]` 引用角标，而对业务事实不标引用编号
- 职责单一：回答节点只生成文本，绝不直接触发任何写操作

铁律：知识型问题没有检索到依据时，不许编造，直接说明未检索到并给出三个可执行的下一步建议。
"""

from __future__ import annotations

from typing import Any

from ..llm import get_chat_model
from ..prompts.service_desk import ANSWER_SYSTEM_PROMPT
from ..state import TicketState


def _format_evidence(evidence: list[dict[str, Any]]) -> str:
    lines = []
    for item in evidence:
        # 出处尽量给到「第 X 章 · X.Y 节」，模型才好标 [1][2]
        where = " · ".join(
            part for part in (item.get("chapter", ""), item.get("section", "")) if part
        )
        heading = f"（{where}）" if where else ""
        lines.append(f"[{item['idx']}] {item['title']}{heading}：{item.get('snippet', '')}")
    return "\n".join(lines)


def _format_facts(facts: list[dict[str, Any]]) -> str:
    """把只读查到的工单现状排成清单。事实不标引用编号（它不是制度）。"""
    lines = []
    for item in facts:
        bits = [
            f"单号 {item.get('ticket_no', '')}",
            f"状态 {item.get('status', '')}",
            f"优先级 {item.get('urgency', '')}",
        ]
        if item.get("title"):
            bits.append(f"标题 {item['title']}")
        bits.append(f"提单人 {item.get('reporter', '')}")
        if item.get("created_at"):
            bits.append(f"创建于 {item['created_at']}")
        if item.get("resolution"):
            bits.append(f"处理结论 {item['resolution']}")
        lines.append("- " + "；".join(bits))
    return "\n".join(lines)


def _no_evidence_reply(query: str) -> str:
    """没检索到依据：这是产品规则（不许编），不是模型降级。"""
    return (
        f"知识库里没有检索到和「{query}」直接相关的规定，我不能凭空给结论。\n\n"
        "下一步有三个选择：\n"
        "1. 换个说法再问一次（比如带上系统名、报错码）；\n"
        "2. 我帮你建一张工单，让对应的同事跟进；\n"
        "3. 你告诉我大概属于哪个方向（账号权限 / 财务报销 / 考勤假期 / 系统故障），我再查一遍。"
    )


def _llm_answer(state: TicketState) -> str:
    """把"制度"和"这几张单的现状"一起交给模型，要求结论标 [编号]、事实不标。"""
    evidence = state.get("policy_evidence") or []
    facts = state.get("facts") or []
    policy_block = _format_evidence(evidence) or "（没有检索到相关制度）"
    facts_block = _format_facts(facts) or "（这次没有查到具体工单）"
    user_content = (
        f"员工的问题：{state.get('query')}\n\n"
        f"知识库资料（制度，回答时标引用编号）：\n{policy_block}\n\n"
        f"业务事实（只读查到的工单现状，不是制度，不要标引用）：\n{facts_block}\n\n"
        "请按系统提示要求作答。"
    )
    message = get_chat_model().invoke(
        [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
    )
    return str(message.content).strip()


def answer_with_citations(state: TicketState) -> dict[str, Any]:
    """生成带引用的回答（知识型链路）。制度与事实都没有时才认怂，不调模型。"""
    evidence = state.get("policy_evidence") or []
    facts = state.get("facts") or []
    if not evidence and not facts:
        return {"reply": _no_evidence_reply(state.get("query") or ""), "via": "kb_miss"}

    # 只有事实、没有制度时也算答出来了，但 via 标出来，便于排查"制度为什么没命中"
    via = "kb_hit" if evidence else "kb_facts_only"
    return {"reply": _llm_answer(state), "via": via}