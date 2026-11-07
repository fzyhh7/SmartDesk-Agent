"""FastAPI 接入层：负责解析 HTTP 请求、构造 UserContext 并调用主图或只读工具。

分工（不把业务逻辑写进路由）：
- 路由只做三件事：解析请求 → 组 `UserContext`（谁 / 哪个租户 / 什么角色）→ 调 `get_graph()`。
- Agent 的全部编排逻辑都在 `backend/app/agents/` 里，这一层不 import 任何具体节点，也不判权限。
- 权限判定的唯一位置是 MCP server（`backend/app/mcp/servers/guard.py`）。

目录：
    main.py        FastAPI 应用入口与 /health 健康检查
    deps.py        身份依赖（请求头 → UserContext）
    schemas.py     请求 / 响应 Pydantic 模型
    streaming.py   把 graph.stream(...) 翻译成前端认识的 6 种 SSE 事件流
    routes.py      全部 HTTP 路由（流式对话 / 断点恢复 / 状态查询 / 工单与审批列表）
"""
