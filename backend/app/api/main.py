"""FastAPI 鍏ュ彛锛歚uvicorn backend.app.api.main:app --reload --port 8010`銆?
鑱岃矗鍙湁鍥涗欢浜嬶細CORS锛堢粰 Vue3 鐢級銆佹寕璺敱銆佸仴搴锋鏌ャ€佺粺涓€寮傚父鍏滃簳銆?Agent 閫昏緫涓€琛岄兘涓嶅湪杩欓噷鈥斺€旇繖涓€灞傚潖浜嗭紝CLI 鐓ф牱鑳借窇锛岃繖灏辨槸鍒嗗眰鐨勬剰涔夈€?"""

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
    """鍚姩鏃剁紪璇戜竴娆′富鍥撅紙棣栨璇锋眰涓嶅繀鍐嶇瓑缂栬瘧锛屼篃椤烘墜鏆撮湶閰嶇疆閿欒锛夈€?""
    from ..agents.graph import get_graph

    get_graph()
    logger.info("涓诲浘缂栬瘧瀹屾垚锛屾湇鍔″凡灏辩华锛?s", API_PREFIX)
    yield


def create_app() -> FastAPI:
    """宸ュ巶鍑芥暟锛堟柟渚夸互鍚庢祴璇?澶氬疄渚嬶紱`app` 鍦ㄦ枃浠舵湯灏惧垱寤猴級銆?""
    app = FastAPI(
        title="SmartDesk-Agent 鏈嶅姟鍙?Agent",
        version="1.0.0",
        description=(
            "浼佷笟鍐呴儴鏈嶅姟鍙?Agent 鐨?HTTP 灞傦細鐭ヨ瘑闂瓟 / 寤哄崟 / 瀹℃壒 / 澶氱鎴枫€俓n\n"
            "韬唤璧拌姹傚ご锛歚X-User-Id`銆乣X-Tenant-Id`銆乣X-Roles`锛堥€楀彿鍒嗛殧锛夈€?
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

    @app.get("/health", tags=["ops"], summary="瀛樻椿鎺㈤拡")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        """鍏滃簳锛氭妸寮傚父鍙樻垚 JSON锛屽埆璁╂祻瑙堝櫒鏀跺埌涓€鍧?HTML 鍫嗘爤銆?""
        logger.exception("鏈鐞嗗紓甯革細%s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}", "path": request.url.path},
        )

    return app


app = create_app()

