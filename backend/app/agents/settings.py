"""集中读取环境变量，避免节点里到处 os.getenv。

三种外部依赖都可以"缺省但不崩"：
- 没有 DEEPSEEK_API_KEY：直接报错（本项目不提供规则版实现）；
- 没有 Postgres：checkpointer 自动回退 SQLite（本机演示用）；
- 没有 Milvus / DASHSCOPE_API_KEY：直接报错，请先 docker compose 起 PG / Milvus 并配好 key。

所有环境变量在此集中收敛，通过 UserContext / settings 传进节点，业务节点内不直接读 os.getenv。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# 仓库根目录：backend/app/agents/settings.py -> 上三级
ROOT_DIR = Path(__file__).resolve().parents[3]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


# 可选：从仓库根 .env / backend/.env 读取（装了 python-dotenv 才生效，不装也能跑）
try:  # pragma: no cover - 只在存在 .env 时生效
    from dotenv import load_dotenv

    for _candidate in (ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"):
        if _candidate.exists():
            load_dotenv(_candidate, override=False)
except Exception:  # noqa: BLE001
    pass


@dataclass(frozen=True)
class Settings:
    # ---------- LLM ----------
    api_key: str = _env("DEEPSEEK_API_KEY")
    base_url: str = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model: str = _env("AGENT_TRANSPORT_MODEL", "deepseek-chat")
    temperature: float = float(_env("AGENT_TEMPERATURE", "0") or 0)

    # ---------- 状态库（checkpoint）----------
    # postgres: 生产用；sqlite: 无 PG 时的降级
    checkpoint_backend: str = _env("AGENT_CHECKPOINT_BACKEND", "postgres").lower()
    database_url: str = _env(
        "DATABASE_URL", "postgresql://smartdesk:smartdesk@localhost:5432/smartdesk"
    )
    # SQLite 兜底文件
    db_path: Path = Path(_env("AGENT_DB_PATH", str(ROOT_DIR / ".data" / "agent.sqlite")))

    # ---------- 向量库（Milvus）----------
    milvus_uri: str = _env("MILVUS_URI", "http://localhost:19530")
    milvus_collection: str = _env("MILVUS_COLLECTION", "smartdesk_kb")
    milvus_timeout: float = float(_env("MILVUS_TIMEOUT", "5") or 5)

    # ---------- Embedding ----------
    # DashScope 兼容模式（text-embedding-v4，1024 维）；没 key 会直接报错（见 rag/embedding.py）
    embedding_api_key: str = _env("DASHSCOPE_API_KEY") or _env("EMBEDDING_API_KEY")
    embedding_base_url: str = _env(
        "EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    embedding_model: str = _env("EMBEDDING_TRANSPORT_MODEL", "text-embedding-v4")
    embedding_dim: int = int(_env("EMBEDDING_DIM", "1024") or 1024)
    # DashScope 兼容端点单次 embedding 最多 10 条，LangChain 按这个值分批
    embedding_batch_size: int = int(_env("EMBEDDING_BATCH_SIZE", "10") or 10)

    # ---------- Rerank（Cross-Encoder 精排，二级检索漏斗）----------
    # 默认开启并直接复用 DASHSCOPE_API_KEY 调 gte-rerank-v2：
    # 先由 Milvus RRF 融合出 candidate_k 条粗排候选，再经 Cross-Encoder 交叉注意力重排取最终 top-k。
    # 设 RERANK_ENABLED=false 可一键退回纯 RRF（便于跑 A/B 对照实验）；接口超时或报错时自动回退 RRF。
    rerank_enabled: bool = _env("RERANK_ENABLED", "true").lower() not in ("0", "false", "no", "off")
    rerank_api_key: str = _env("RERANK_API_KEY") or _env("DASHSCOPE_API_KEY") or _env("EMBEDDING_API_KEY")
    rerank_url: str = _env(
        "RERANK_URL",
        "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
    )
    rerank_model: str = _env("RERANK_MODEL", "gte-rerank-v2")
    rerank_candidate_k: int = int(_env("RERANK_CANDIDATE_K", "10") or 10)
    rerank_timeout: float = float(_env("RERANK_TIMEOUT", "6") or 6)

    # ---------- PDF 解析（MinerU 官方 SDK）----------
    # 精准解析模式需要 token（mineru.net 免费申请）；轻量 flash 模式免登录
    mineru_api_key: str = _env("MINERU_API_KEY") or _env("MINERU_TOKEN")
    mineru_mode: str = _env("MINERU_MODE", "flash").lower()  # flash | precision
    mineru_ocr: bool = _env("MINERU_OCR", "false").lower() in ("1", "true", "yes")
    mineru_language: str = _env("MINERU_LANGUAGE", "ch")
    mineru_timeout: int = int(_env("MINERU_TIMEOUT", "300") or 300)

    # 知识库原始文档目录（PDF 放这里，入库脚本扫它）
    kb_source_dir: Path = Path(_env("KB_SOURCE_DIR", str(ROOT_DIR / "docs" / "kb" / "pdf")))
    # 默认租户：CLI / 评测 / 知识库入库都用它，多租户隔离靠这个值做 filter
    default_tenant: str = _env("DEFAULT_TENANT", "tenant-demo")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_api_key)

    @property
    def rerank_active(self) -> bool:
        """精排开关开启且有可用 Key 时生效。"""
        return bool(self.rerank_enabled and self.rerank_api_key)

    @property
    def mineru_precise_enabled(self) -> bool:
        """precision 模式必须有 token；flash 模式免登录也能用。"""
        return bool(self.mineru_api_key)


settings = Settings()


def ensure_data_dir() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)