"""请求 / 响应模型（Pydantic v2）。

只定义"这一层真正需要"的字段：路由不复制 Agent 的 State，
所以响应里给的是前端要用的那几个：status / reply / 引用 / 审批卡片。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """发一句话（一次 invoke）。"""

    message: str = Field(min_length=1, max_length=2000, description="员工说的话")
    thread_id: str = Field(default="t1", max_length=64, description="会话 id（= thread_id）")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "年假有多少天？", "thread_id": "web-1"}
        }
    }


class ResumeRequest(BaseModel):
    """从暂停点继续：三种闸门各自吃不同形状，这里统一成三种写法之一。

    - 澄清门：{"answers": {"ticket_no": "TK-20261102-0001"}}
    - 确认/审批门：{"decision": {"type": "approve" | "edit" | "reject", "patch": {...}, "message": "..."}}
    - 只读动作/闲聊不会暂停，用不到这个接口
    """

    answers: dict[str, Any] | None = Field(default=None, description="澄清门的补充参数")
    decision: dict[str, Any] | None = Field(default=None, description="确认/审批门的决定")
    type: Literal["approve", "edit", "reject"] | None = Field(
        default=None, description="decision 的简写（等价于 decision.type）"
    )
    patch: dict[str, Any] | None = Field(default=None, description="edit 时改了哪些字段")
    message: str = Field(default="", max_length=500, description="驳回理由 / 备注")

    model_config = {
        "json_schema_extra": {
            "example": {"decision": {"type": "approve"}}
        }
    }

    def to_resume_payload(self) -> dict[str, Any]:
        """翻译成 `human_gate.normalize_human_input` 认识的形状。"""
        if self.answers is not None:
            return {"answers": self.answers}
        if self.decision is not None:
            return {"type": "decision", "decision": self.decision}
        kind = self.type or "approve"
        return {
            "type": "decision",
            "decision": {"type": kind, "patch": self.patch or {}, "message": self.message},
        }
