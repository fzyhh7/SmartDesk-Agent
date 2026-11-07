"""主图：9 个节点，四条路。

一句话读法（每个节点名都是动词短语）：
    classify_request → gather_evidence → answer_with_citations → compose_reply      （知识型）
                                      ↘ plan_action → confirm_action / approve_action / ask_missing_info
                                                      → execute_action → compose_reply

两处容易讲错的地方（面试常问）：
- confirm_action 不是"确认完就执行"：员工可能在卡片上改出**不可逆**参数（关单加"通知提单人"），
  所以确认后还要按新参数重算风险，需要时补一道 approve_action（route_after_confirm）。
- approve_action 里"发起"和"批准"是两件事：员工发起不可逆动作只会进 pending 队列，
  能不能点通过看**恢复那一刻的身份**（主管拿同一个 thread_id resume 就能批）。

路由统一写在本文件：每个条件边配一个**纯函数 router**，节点只负责"算 + 返回字段"。
这样分支决策集中在一处、可读可测，而不是在各个节点内部散落跳转逻辑。
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

# gate → 节点名：plan_action 只写 gate（clarify/confirm/approve/execute），不决定去哪
GATE_TO_NODE: dict[str, str] = {
    "clarify": "ask_missing_info",
    "confirm": "confirm_action",
    "approve": "approve_action",
    "execute": "execute_action",
}


# 路由函数一律"直接返回目标节点名的精确 Literal"：
# 这样 LangGraph draw_mermaid() 只会画出真实可达的边，图结构一目了然。
def route_after_classify(state: TicketState) -> Literal["compose_reply", "gather_evidence"]:
    """闲聊不查资料；其余都要先取证据。"""
    return "compose_reply" if state.get("intent") == "chat" else "gather_evidence"


def route_after_gather(state: TicketState) -> Literal["plan_action", "answer_with_citations"]:
    """要动手（动作型）才进 plan_action；问知识直接答。"""
    return "plan_action" if state.get("intent") == "action" else "answer_with_citations"


def route_after_plan(
    state: TicketState,
) -> Literal["compose_reply", "ask_missing_info", "confirm_action", "approve_action", "execute_action"]:
    """没办成（denied / rejected / failed）→ 回复；否则按 gate 进对应的门。"""
    if state.get("outcome"):
        return "compose_reply"
    gate = state.get("gate") or "execute"
    return GATE_TO_NODE.get(gate, "execute_action")  # type: ignore[return-value]


def route_after_confirm(
    state: TicketState,
) -> Literal["compose_reply", "approve_action", "execute_action"]:
    """被拒/没资格 → 回复；改出不可逆参数 → 补一道审批；否则直接执行。"""
    if state.get("outcome"):
        return "compose_reply"
    return "approve_action" if state.get("gate") == "approve" else "execute_action"


def route_after_human(state: TicketState) -> Literal["compose_reply", "execute_action"]:
    """没人批 / 执行前就失败 → 回复；批过了 → 执行。"""
    return "compose_reply" if state.get("outcome") else "execute_action"



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