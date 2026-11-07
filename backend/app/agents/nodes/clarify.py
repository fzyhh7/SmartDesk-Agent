"""clarify 闸门：信息不够时，AI 反过来问员工（第一类人类介入）。

中断与恢复机制：
- 节点里调用 `interrupt(payload)` 会暂停整张图，payload 通过 `response["__interrupt__"]` 交给前端渲染
- 恢复时用 `invoke(Command(resume=...), config)`，凭同一个 `thread_id` 从断点接着跑
- 状态持久化依赖 checkpointer（PostgresSaver 优先，SqliteSaver 兜底）

恢复后的行为：
- 拿到 answers 合并进 action.args
- 回到 plan_action 重新组装草稿（可能仍有缺口，会再次暂停，直到参数齐）
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from ..state import TicketState
from .action_spec import summary_of
from .human_gate import normalize_human_input

QUESTIONS = {
    "ticket_no": "请提供工单号（形如 TK-20261031-0001），我按单号去查/改/关。",
    "patch": "你想改哪个字段？例如「优先级改成高」「状态改成处理中」。",
    "title": "工单标题写什么？一句话说清现象就行（例如：财务系统登录失败）。",
    "content": "要发布的内容是什么？可以把处理过程直接贴给我。",
    "op": "你要我做什么？建单、改单、关单，还是把经验发到知识库？",
}


def _question_for(missing: list[str], facts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """缺参数时问什么。

    名下有多张单时先把单号列出来让员工点一张：批量执行写操作风险太大，
    这里选择"不猜、不批量"，而不是替员工决定改哪一张。
    """
    numbers = [str(item.get("ticket_no")) for item in facts if item.get("ticket_no")]
    if missing and missing[0] == "ticket_no" and len(numbers) > 1:
        return (
            f"你名下有 {len(numbers)} 张单，我不会一次性批量处理；请指定其中一张：" + "、".join(numbers),
            numbers,
        )
    if missing:
        return QUESTIONS.get(missing[0], "还差一点信息，能再补一句吗？"), numbers
    return "还需要补充信息。", numbers


def ask_missing_info(state: TicketState) -> dict[str, Any]:
    """缺参数时问人一句（AI 问、员工答），答完回 plan_action 重算。"""
    action = state.get("action") or {}
    missing = list(action.get("missing") or [])
    question, options = _question_for(missing, state.get("facts") or [])

    payload = {
        "type": "clarify",
        "question": question,
        "missing": missing,
        "options": options,
        "title": summary_of(action),
        "hint": "回答后会从断点继续，不需要重新描述一遍。",
    }
    answer = interrupt(payload)
    parsed = normalize_human_input(answer)
    answers = parsed.get("answers") or {}

    action = state.get("action") or {}
    args = {**(action.get("args") or {}), **answers}
    update = {
        "action": {**action, "args": args, "missing": []},
        "reply": None,
    }
    return update