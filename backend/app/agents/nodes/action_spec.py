"""动作的"规格表"：风险等级、工具归属的服务、风险到闸门的映射、字段中文名。

这个文件只放表和"读表的函数"，不放流程。想改 Agent 的行为（比如"关单+通知要审批"），
先来这里改表，通常不用碰节点逻辑——这也是面试里"你的策略写在哪"的答案。
"""

from __future__ import annotations

from typing import Any

# 每个 op 归哪个 MCP server 管。为什么不在 classify 让模型输出：
# 这是 op 的 1:1 确定性映射，模型多吐一个字段只多一个能填错的地方。
SERVER_BY_OP: dict[str, str] = {
    "search_kb": "kb",
    "publish_kb_article": "kb",
}
DEFAULT_SERVER = "ticket"


def server_of(op: str) -> str:
    """op → server 名字（唯一的推导入口，plan_action 与 execute 都从这里取）。"""
    return SERVER_BY_OP.get(op or "", DEFAULT_SERVER)


# 每个工具"默认"多危险（read 直通 / write_reversible 确认 / write_irreversible 审批）
RISK_BY_OP: dict[str, str] = {
    "query_ticket": "read",
    "list_tickets": "read",
    "search_kb": "read",
    "create_ticket": "write_reversible",
    "update_ticket": "write_reversible",
    "close_ticket": "write_reversible",
    "publish_kb_article": "write_irreversible",
}


def compute_risk(op: str, args: dict[str, Any], base: str) -> str:
    """风险不只由"调哪个工具"决定，还要看"带什么参数"（本项目拓展）。

    - close_ticket 默认可撤销（能重开）；一旦 notify_reporter=True 就会对外发消息，
      撤不回来 → 升级为 write_irreversible，必须走审批。
    - publish_kb_article 发布出去全员可见 → 审批。
    """
    if op == "close_ticket" and bool(args.get("notify_reporter")):
        return "write_irreversible"
    if op == "publish_kb_article":
        return "write_irreversible"
    return base


# 风险 → 第几道闸门（read 直通执行，不需要人）
GATE_BY_RISK: dict[str, str] = {
    "read": "execute",
    "write_reversible": "confirm",
    "write_irreversible": "approve",
}

# 卡片上给人看的字段中文名（模型填的是英文 key）
FIELD_LABELS: dict[str, str] = {
    "title": "标题",
    "description": "描述",
    "urgency": "优先级",
    "category": "分类",
    "reporter": "提单人",
    "ticket_no": "工单号",
    "patch": "要改的字段",
    "resolution": "解决说明",
    "notify_reporter": "通知提单人",
    "content": "正文",
    "tags": "标签",
    "change_note": "变更说明",
    "status": "状态",
    "limit": "条数",
}

# --------------------------------------------------------------------------- #
# 视图：卡片上的字段 / 标题都从 action 现算，不再另存一份"草稿"
# --------------------------------------------------------------------------- #
EDITABLE_BLOCK = {"reporter", "tenant_id"}  # 身份字段不许在卡片上改


def label_of(action: dict[str, Any]) -> str:
    """动作中文名，例如「关工单」。"""
    return str((action or {}).get("label") or "操作")


def summary_of(action: dict[str, Any]) -> str:
    """确认卡/审批卡的一句话摘要，避免出现「建工单：建工单：…」。"""
    args = (action or {}).get("args") or {}
    label = label_of(action)
    head = str(args.get("title") or args.get("ticket_no") or "").strip()
    for prefix in (f"{label}：", f"{label}:", label):
        if head.startswith(prefix):
            head = head[len(prefix):].strip()
            break
    return f"{label}：{head}" if head else label


def fields_of(action: dict[str, Any]) -> list[dict[str, Any]]:
    """把 args 变成前端能直接渲染的卡片字段（值 + 中文标签 + 来源 + 能否编辑）。"""
    args = (action or {}).get("args") or {}
    sources = (action or {}).get("sources") or {}
    return [
        {
            "name": name,
            "label": FIELD_LABELS.get(name, name),
            "value": value,
            "source": sources.get(name, "agent_inferred"),
            "editable": name not in EDITABLE_BLOCK,
        }
        for name, value in args.items()
    ]
