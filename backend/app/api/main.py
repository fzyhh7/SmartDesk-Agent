"""FastAPI 入口：`uvicorn backend.app.api.main:app --reload --port 8010`。

职责只有四件事：CORS（给 Vue3 用）、挂路由、健康检查、统一异常兜底。
Agent 逻辑一行都不在这里——这一层坏了，CLI 照样能跑，这就是分层的意义。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动时编译一次主图（首次请求不必再等编译，也顺手暴露配置错误）。"""
    from ..agents.graph import get_graph

    get_graph()
    logger.info("主图编译完成，服务已就绪：%s", API_PREFIX)
    yield


def create_app() -> FastAPI:
    """工厂函数（方便以后测试/多实例；`app` 在文件末尾创建）。"""
    app = FastAPI(
        title="SmartDesk-Agent 服务台 Agent",
        version="1.0.0",
        description=(
            "企业内部服务台 Agent 的 HTTP 层：知识问答 / 建单 / 审批 / 多租户。\n\n"
            "身份走请求头：`X-User-Id`、`X-Tenant-Id`、`X-Roles`（逗号分隔）。"
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vue3 dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=API_PREFIX)

    @app.get("/health", tags=["ops"], summary="存活探针")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        """兜底：把异常变成 JSON，别让浏览器收到一坨 HTML 堆栈。"""
        logger.exception("未处理异常：%s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}", "path": request.url.path},
        )

    return app


app = create_app()

