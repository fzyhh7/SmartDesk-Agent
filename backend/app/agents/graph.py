"""主图：9 个节点、5 条条件边（业务上走 4 条路：闲聊直答 / 知识问答 / 动作过闸门 / 澄清补参）。

一句话读法（每个节点名都是动词短语）：
    classify_request → gather_evidence → answer_with_citations → compose_reply      （知识型）
                                      ↘ plan_action → confirm_action / approve_action / ask_missing_info
                                                      → execute_action → compose_reply

两处容易被误读的实现细节（改图之前先看这两行）：
- confirm_action 不是"确认完就执行"：员工可能在卡片上改出**不可逆**参数（关单加"通知提单人"），
  所以确认后还要按新参数重算风险，需要时补一道 approve_action（route_after_confirm）。
- approve_action 里"发起"和"批准"是两件事：员工发起不可逆动作只会进 pending 队列，
  能不能点通过看**恢复那一刻的身份**（主管拿同一个 thread_id resume 就能批）。

路由本文件只管**装配**：五个条件边的判断函数在 `routing.py`（纯函数、零第三方依赖，
`tests/test_routing.py` 直接断言「什么状态 → 下一跳是谁」，不用起 langgraph）。
唯一会让图"停下来"的是三个闸门里的 `interrupt()`（ask_missing_info / confirm_action / approve_action）。
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from .checkpoint import get_checkpointer
from .nodes.answer import answer_with_citations
from .nodes.classify import classify_request
from .nodes.clarify import ask_missing_info
from .nodes.execute import execute_action
from .nodes.gather_evidence import gather_evidence
from .nodes.human_gate import approve_action, confirm_action
from .nodes.plan_action import plan_action
from .nodes.respond import compose_reply
from .routing import (
    GATE_TO_NODE,
    route_after_classify,
    route_after_confirm,
    route_after_gather,
    route_after_human,
    route_after_plan,
)
from .state import TicketState, UserContext

NodeName = Literal[
    "classify_request",
    "gather_evidence",
    "answer_with_citations",
    "plan_action",
    "ask_missing_info",
    "confirm_action",
    "approve_action",
    "execute_action",
    "compose_reply",
]

# 路由函数一律"直接返回目标节点名的精确 Literal"：
# 这样 LangGraph draw_mermaid() 只会画出真实可达的边，图结构一目了然。
# 实现放在 `routing.py`（纯函数、零第三方依赖），本文件只负责接到边上。


def compile_graph(*, checkpointer=None):
    """装配并编译主图（`checkpointer=None` 时用全局默认：PG 优先、失败退 SQLite）。"""
    builder = StateGraph(TicketState, context_schema=UserContext)

    builder.add_node("classify_request", classify_request)
    builder.add_node("gather_evidence", gather_evidence)
    builder.add_node("answer_with_citations", answer_with_citations)
    builder.add_node("plan_action", plan_action)
    builder.add_node("ask_missing_info", ask_missing_info)
    builder.add_node("confirm_action", confirm_action)
    builder.add_node("approve_action", approve_action)
    builder.add_node("execute_action", execute_action)
    builder.add_node("compose_reply", compose_reply)

    builder.add_edge(START, "classify_request")
    builder.add_conditional_edges("classify_request", route_after_classify)
    builder.add_conditional_edges("gather_evidence", route_after_gather)
    builder.add_edge("answer_with_citations", "compose_reply")
    builder.add_conditional_edges("plan_action", route_after_plan)
    builder.add_edge("ask_missing_info", "plan_action")  # 补完参数回去重算计划
    builder.add_conditional_edges("confirm_action", route_after_confirm)
    builder.add_conditional_edges("approve_action", route_after_human)
    builder.add_edge("execute_action", "compose_reply")
    builder.add_edge("compose_reply", END)

    saver = checkpointer if checkpointer is not None else get_checkpointer()
    return builder.compile(checkpointer=saver)


_GRAPH = None


def get_graph():
    """进程内单例（编译一次，之后复用；checkpointer 自己带连接）。"""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = compile_graph()
    return _GRAPH