"""classify 节点：先判断"员工在问知识、还是在要动作、还是在闲聊"。

设计要点：
- 用 `with_structured_output(Classification, method="json_mode")` 让模型输出结构化分类结果
- 节点只负责计算并返回需要更新的 State 字段，下一跳去哪由 `graph.py` 中的 `route_after_classify` 条件边决定

模型调用失败必须报错（没有规则兜底）：见 llm.py 的"缺 key 直接抛异常"。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from ..llm import get_chat_model
from ..prompts.service_desk import CLASSIFY_SYSTEM_PROMPT
from ..state import TicketState


class Classification(BaseModel):
    """模型侧的结构化输出：意图、动作、主题，以及"这句话提到了哪张单"。

    只让模型判断"代码推不出来"的东西：
    - 风险等级不在这里：它是业务规则，由 plan_action 查 RISK_BY_OP + compute_risk 按参数算；
    - MCP server 不在这里：op 就能决定（publish_kb_article → kb，其余 → ticket）。
    """

    intent: Literal["knowledge", "action", "chat"] = Field(description="员工在问知识 / 要动作 / 闲聊")
    op: str = Field(default="none", description="动作类型：create_ticket / close_ticket / update_ticket / list_tickets / query_ticket / publish_kb_article / none")
    topic: str = Field(default="其他", description="业务主题")
    summary: str = Field(default="", description="一句话概括员工诉求（<=40 字）")
    urgency: Literal["low", "medium", "high"] = Field(default="medium")
    # 下面两个字段专门给"取证据"用：它和 intent/op 是两条独立的轴
    # （知识型问题也会提到单号："TK-… 按规定能不能延期"）。
    reference: Literal["none", "number", "my_last", "my_recent"] = Field(
        default="none",
        description="提到了哪张单：none=没提；number=有明确单号；my_last=我的最近一张；my_recent=我的好几张",
    )
    reference_hint: str = Field(default="", description="原话里指向这张单的片段，照抄，不要编造单号")


def extract_query(state: TicketState) -> str:
    """取本轮用户输入：优先 state["query"]，否则取最后一条 HumanMessage。"""
    query = (state.get("query") or "").strip()
    if query:
        return query
    for message in reversed(state.get("messages") or []):
        if getattr(message, "type", "") == "human":
            return str(message.content).strip()
    return ""


def _classify_with_llm(query: str) -> Classification:
    """调模型做结构化分类。

    DeepSeek 目前只支持 response_format=json_object（不支持 json_schema），
    所以用 method="json_mode"，并把字段说明拼进 system prompt。
    """
    model = get_chat_model()
    parser = PydanticOutputParser(pydantic_object=Classification)
    chain = model.with_structured_output(Classification, method="json_mode")
    result = chain.invoke(
        [
            ("system", CLASSIFY_SYSTEM_PROMPT + "\n\n" + parser.get_format_instructions()),
            ("human", query),
        ]
    )
    if not isinstance(result, Classification):
        result = Classification.model_validate(result)
    return result


def classify_request(state: TicketState) -> dict[str, Any]:
    """看懂这句话：在提问 / 在命令 / 在闲聊，给出 intent 与动作类型。"""
    query = extract_query(state)
    result = _classify_with_llm(query)

    action: dict[str, Any] | None = None
    if result.intent == "action" and result.op not in {"", "none"}:
        action = {"op": result.op, "args": {}, "missing": []}

    update: dict[str, Any] = {
        "query": query,
        "intent": result.intent,
        "action": action,
        # 风险由 plan_action 按 op + 参数重算，这里先按最低档占位
        "risk": "read",
        "classification": {
            "topic": result.topic,
            "summary": result.summary or query[:40],
            "urgency": result.urgency,
            # 取证据用：模型只给"是哪一类指代"，不给单号值（单号由正则校验，防编造）
            "reference": result.reference,
            "reference_hint": result.reference_hint,
        },
    }

    if result.intent == "chat":
        update["reply"] = None
    return update