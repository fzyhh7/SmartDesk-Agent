"""PDF → Markdown：用 MinerU 官方 SDK（mineru-open-sdk）。

为什么不用 PyPDFLoader：普通 PDF 抽文本会把左右分栏、表格、页眉页脚全搅在一起，
MinerU 这类版面解析工具输出的是 **Markdown**（标题层级 + 还原后的表格），
后面才能做「结构感知切分」。

两种模式（SDK 里就是两个方法）：
- flash：轻量解析，免登录，适合 <=20 页的文档（我们要用的制度 PDF 都在这范围内）；
- precision：精准解析，需要 MINERU_API_KEY（mineru.net 免费申请），支持更大页数。

本模块只做「拿 Markdown」，不负责切分（切分见 splitter.py），也不碰向量库。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..settings import settings


class MinerUUnavailable(RuntimeError):
    """MinerU 调不通（没装 SDK / 没配 token / 网络或额度问题）。"""


@dataclass(frozen=True)
class ParsedDocument:
    """一份解析完的文档。markdown 是唯一真正重要的东西。"""

    source: str
    markdown: str
    mode: str
    elapsed_s: float
    task_id: str = ""
    image_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def stem(self) -> str:
        """文件名主干，用来当文档 title / doc_id 的一部分。"""
        name = self.source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return Path(name).stem


def _client(require_token: bool) -> "Any":
    """延迟导入 SDK：没装也不影响其它链路。"""
    try:
        from mineru import MinerU
    except ImportError as exc:  # pragma: no cover - 依赖缺失时才走到
        raise MinerUUnavailable(
            "缺少依赖 mineru-open-sdk，请执行：uv pip install mineru-open-sdk"
        ) from exc

    token = settings.mineru_api_key or None
    if require_token and not token:
        raise MinerUUnavailable(
            "precision 模式需要 MINERU_API_KEY（或 MINERU_TOKEN）："
            "请到 https://mineru.net/ 创建 Token，写进项目根目录 .env（我不读你的值）"
        )
    return MinerU(token=token)


def parse(
    source: str | Path,
    *,
    mode: str | None = None,
    ocr: bool | None = None,
    language: str | None = None,
    timeout: int | None = None,
) -> ParsedDocument:
    """把一个 PDF（本地路径或公网 URL）解析成 Markdown。

    mode: "flash"（默认，免 token）| "precision"（需 token）
    ocr:  扫描件才需要 True；文本型 PDF 保持 False 更快
    """
    mode = (mode or settings.mineru_mode or "flash").lower()
    if mode not in ("flash", "precision"):
        raise ValueError(f"未知的 MinerU 模式：{mode}（只能是 flash 或 precision）")

    ocr_flag = settings.mineru_ocr if ocr is None else ocr
    lang = language or settings.mineru_language
    wait = timeout or settings.mineru_timeout
    src = str(source)
    started = time.perf_counter()

    try:
        client = _client(require_token=(mode == "precision"))
        if mode == "flash":
            result = client.flash_extract(
                src,
                language=lang,
                is_ocr=ocr_flag,
                enable_formula=True,
                enable_table=True,
                timeout=wait,
            )
        else:
            result = client.extract(src, ocr=ocr_flag, language=lang, timeout=wait)
    except MinerUUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - SDK 的异常类型很多，统一包装
        raise MinerUUnavailable(f"MinerU 解析失败（{mode}）：{type(exc).__name__}: {exc}") from exc

    markdown = getattr(result, "markdown", None)
    if not markdown:
        raise MinerUUnavailable(f"MinerU 返回里没有 markdown（task_id={getattr(result, 'task_id', '')}）")

    return ParsedDocument(
        source=src,
        markdown=markdown,
        mode=mode,
        elapsed_s=round(time.perf_counter() - started, 2),
        task_id=getattr(result, "task_id", "") or "",
        image_count=len(getattr(result, "images", []) or []),
        extra={"ocr": ocr_flag, "language": lang},
    )


def parse_many(sources: list[str | Path], **kwargs: Any) -> list[ParsedDocument]:
    """批量解析；单个失败不拖垮整批，失败信息放进返回值之外的日志由调用方处理。"""
    docs: list[ParsedDocument] = []
    for src in sources:
        docs.append(parse(src, **kwargs))
    return docs