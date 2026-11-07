"""环境变量体检：只报告「已设置 / 未设置」，绝不打印任何值。

用法：
    python -m scripts.env_status
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.agents.settings import ROOT_DIR, settings  # noqa: E402

SECRETS = [
    ("DEEPSEEK_API_KEY", "LLM（DeepSeek/OpenAI 兼容）"),
    ("DASHSCOPE_API_KEY", "Embedding + Rerank（text-embedding-v4 / gte-rerank-v2）"),
]

OTHERS = [
    ("DATABASE_URL", "PostgreSQL 连接串（含口令，只显示是否可用）"),
    ("MILVUS_URI", "Milvus 地址"),
]


def _flag(exists: bool, hint_on: str, hint_off: str) -> str:
    return ("已设置 → " + hint_on) if exists else ("未设置（必填，缺了会直接报错）")


def main() -> int:
    print("=" * 74)
    print("环境变量体检（本命令只输出「是否设置」，不会显示任何值）")
    print("=" * 74)

    print("\n[1] 密钥类（需要你自己填在仓库根 .env）")
    for name, purpose in SECRETS:
        raw = ""
        # 只用 settings 里的布尔判断，不取原始值
        if name == "DEEPSEEK_API_KEY":
            exists = settings.llm_enabled
        else:
            exists = settings.embedding_enabled
        print(f"  {name:22} {purpose:42} {_flag(exists, '真实模型', '缺失')}")

    print("\n[2] 连接类（有默认值，一般不用改）")
    for name, purpose in OTHERS:
        if name == "DATABASE_URL":
            exists = bool(settings.database_url)
        else:
            exists = bool(settings.milvus_uri)
        print(f"  {name:22} {purpose:42} {'有' if exists else '无'}")

    print("\n[3] 当前生效配置（不含任何密钥）")
    print(f"  模型            : {settings.model}")
    print(f"  LLM 可用        : {settings.llm_enabled}")
    mode_desc = (
        f"hybrid + rerank（dense+BM25+RRF Top-{settings.rerank_candidate_k} → {settings.rerank_model}）"
        if settings.rerank_active
        else "hybrid（dense+BM25+RRF）"
    )
    print(f"  Embedding 可用  : {settings.embedding_enabled} → 检索模式 {mode_desc}")
    print(f"  Rerank 启用     : {settings.rerank_active}")
    print(f"  Checkpoint 后端 : {settings.checkpoint_backend}")
    print(f"  Milvus 集合     : {settings.milvus_collection}")

    print("\n[4] 文件检查")
    for rel in (".env", ".env.example", ".gitignore", "pyproject.toml"):
        path = ROOT_DIR / rel
        print(f"  {rel:16} {'存在' if path.exists() else '缺失'}")
    try:
        ignored = ".env" in (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
    except OSError:
        ignored = False
    print(f"  .env 已被 git 忽略 : {ignored}")

    print("\n提示：两个 key 都必须填，缺任何一个，图跑到对应节点会直接报错。")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())