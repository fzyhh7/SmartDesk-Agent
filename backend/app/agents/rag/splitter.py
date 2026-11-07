"""知识库切分：把 MinerU 输出的 Markdown 切成「带章节面包屑」的 chunk。

设计取舍：
1. 先用 Markdown 结构切（标题层级），因为 MinerU 输出的结构是可信的；
2. 结构切出来的块如果仍然超过 `CHUNK_SIZE`，再对超长块做递归字符切分兜底；
3. 每个 chunk 都把「文档名 · 第 X 章 · X.Y 节」拼回正文开头，
   这样 embedding 与 BM25 都能吃到章节信息，回答里的引用也能落到具体小节。

本模块只负责「切」和「补结构」，不联网、不碰向量库。
"""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_text_splitters import (MarkdownHeaderTextSplitter,
                                      RecursiveCharacterTextSplitter)

# —— 切分参数（要调切分就改这里） ——
CHUNK_SIZE = 400
CHUNK_OVERLAP = 60
MIN_CHUNK_CHARS = 30  # 统计用：小于它的 chunk 会单独计数，便于发现问题
MIN_PROSE_CHARS = 10  # 去掉标题行后正文短于它 -> 视为「只有标题」，丢弃
HEADERS_TO_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]
# 文档头部的免责声明/版权声明：每篇都有、内容几乎一样，进向量库会互相抢召回
SKIP_MARKERS = ("技术演示用的虚构示例", "本文档仅供内部使用，请勿外传", "版权所有")
RECURSIVE_SEPARATORS = ["\n\n", "\n", "。", "；", "！", "？", "，", " ", ""]

# —— 清洗 MinerU 输出用的正则 ——
_HTML_TABLE_RE = re.compile(r"<table\b.*?</table>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_BOLD_LINE_RE = re.compile(r"^\*\*(?P<text>[^*]{2,80})\*\*$")
_HEADING_LINE_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
_CHAPTER_RE = re.compile(r"^第\s*[一二三四五六七八九十百零\d]{1,4}\s*[章节篇部]")
_NUMBERED_RE = re.compile(r"^\d+(?:\.\d+){1,3}[\s、.．]")
_DEMO_NOTICE_RE = re.compile(r"^.*技术演示用的虚构示例.*$", re.M)


def _html_table_to_markdown(block: str) -> str:
    """把 MinerU 输出的 <table> 转成 Markdown 表格（否则整张表被当成一坨文字）。"""
    rows: list[list[str]] = []
    for row_html in re.findall(r"<tr\b.*?</tr>", block, re.S | re.I):
        cells = re.findall(r"<t[hd]\b.*?</t[hd]>", row_html, re.S | re.I)
        cells = [html.unescape(_TAG_RE.sub(" ", c)).strip() for c in cells]
        cells = [re.sub(r"\s+", " ", c) or "-" for c in cells]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + ["-"] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |",
             "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _promote_bold_headings(markdown: str) -> str:
    """MinerU 认不出 Word 自定义标题样式时，会把标题输出成整行 `**加粗**`。

    按「第 N 章 / 4.1 / 其余」做有限度猜测，恢复成标题级别，
    否则结构感知切分会把整篇文档当成一个大块。
    """
    if any(line.lstrip().startswith("#") for line in markdown.split("\n")):
        return markdown  # 本身就有标题层级，不动

    out: list[str] = []
    seen_h2 = False
    for line in markdown.split("\n"):
        match = _BOLD_LINE_RE.match(line.strip())
        if not match:
            out.append(line)
            continue
        text = match.group("text").strip()
        if _CHAPTER_RE.match(text):
            out.append(f"## {text}")
            seen_h2 = True
        elif _NUMBERED_RE.match(text):
            out.append(f"### {text}")
        elif not seen_h2 and len(text) <= 40:
            out.append(f"# {text}")  # 文档大标题
        else:
            out.append(line)
    return "\n".join(out)


def _restore_heading_levels(markdown: str) -> str:
    """MinerU 常把「第 1 章」和「1.1 节」都输出成 `##`，层级就丢了。

    这里按文本形态把层级还原：`第 X 章` -> `##`，`X.Y` / `X.Y.Z` -> `###`，
    首个短标题 -> `#`（文档名）。这样切出来的面包屑才带章节。
    """
    lines = markdown.split("\n")
    first_heading_seen = False
    out: list[str] = []
    for line in lines:
        match = _HEADING_LINE_RE.match(line.strip())
        if not match:
            out.append(line)
            continue
        text = match.group("text").strip()
        if _CHAPTER_RE.match(text):
            level = 2
        elif _NUMBERED_RE.match(text):
            level = 3
        elif not first_heading_seen and len(text) <= 40:
            level = 1
        else:
            level = len(match.group("hashes"))
        first_heading_seen = True
        out.append("#" * level + " " + text)
    return "\n".join(out)


def _strip_demo_notice(markdown: str) -> str:
    """去掉「本文档为技术演示用的虚构示例…」声明行，避免它变成一条 chunk。"""
    return _DEMO_NOTICE_RE.sub("", markdown)


def normalize_markdown(markdown: str) -> str:
    """MinerU 输出 -> 标准 Markdown：HTML 表格转 Markdown、退化的加粗标题升级成 #。"""
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _HTML_TABLE_RE.sub(lambda m: _html_table_to_markdown(m.group(0)), text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _promote_bold_headings(text)
    return text


def clean_markdown(markdown: str) -> str:
    """规范化 + 去声明行 + 还原标题层级 + 去图片/注释 + 压空行。"""
    text = normalize_markdown(markdown)
    text = _strip_demo_notice(text)
    text = _restore_heading_levels(text)
    text = _IMAGE_RE.sub("", text)
    text = _HTML_COMMENT_RE.sub("", text)
    lines = [line.rstrip() for line in text.split("\n")]
    return _MULTI_BLANK_RE.sub("\n\n", "\n".join(lines)).strip()


@dataclass(frozen=True)
class Chunk:
    """一个可入库的知识片段。"""

    text: str  # 真正写进 Milvus 的文本（含面包屑）
    content: str  # 纯正文（不含面包屑，给前端展示/引用用）
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        return str(self.metadata.get("doc_id", ""))

    @property
    def chunk_index(self) -> int:
        return int(self.metadata.get("chunk_index", 0))

    @property
    def citation(self) -> str:
        """引用串，例如：星澜科技 员工手册 · 第 4 章 假期管理 · 4.2 年假"""
        return make_citation(
            str(self.metadata.get("title", "")),
            str(self.metadata.get("h1", "")),
            str(self.metadata.get("h2", "")),
            str(self.metadata.get("h3", "")),
        ) or str(self.metadata.get("source_file", ""))


def make_citation(title: str = "", h1: str = "", h2: str = "", h3: str = "") -> str:
    """拼引用串：文档名 · 第 X 章 · X.Y 节（层级去重，空串跳过）。"""
    return " · ".join(_dedupe_parts((title, h1, h2, h3)))


def make_doc_id(tenant_id: str, source_file: str) -> str:
    """文档 id：同一租户 + 同一文件名 -> 稳定 id（重复入库不会造重复文档）。"""
    digest = hashlib.sha1(f"{tenant_id}:{source_file}".encode("utf-8")).hexdigest()
    return f"kb-{digest[:8]}"


def _prose_length(text: str) -> int:
    """去掉 Markdown 标题行后的正文字数（用来判断「是不是只有标题」）。"""
    kept = [line for line in text.split("\n") if not line.lstrip().startswith("#")]
    return len("".join(kept).strip())


def _dedupe_parts(pieces: tuple[str, ...]) -> list[str]:
    """按顺序去重：完全相同或互相包含（「员工手册」vs「员工手册（模板）」）只留信息量大的那个。"""
    parts: list[str] = []
    for raw in pieces:
        piece = (raw or "").strip()
        if not piece:
            continue
        merged = False
        for i, exist in enumerate(parts):
            if piece in exist:
                merged = True
                break
            if exist in piece:
                parts[i] = piece
                merged = True
                break
        if not merged:
            parts.append(piece)
    return parts


_SECTION_NO_RE = re.compile(r"^(\d+(\.\d+)*\s|第\s*[一二三四五六七八九十百零\d]{1,4}\s*[章节篇部])")


def _resolve_title(title: str, text: str, sections: list, stem: str) -> str:
    """文档标题：显式入参 > 第一个 # 标题 > 第一个"不像二级标题"的 h2/h1 > 文件名。

    MinerU 解析出来的 PDF 常把文档大标题也标成 `##`，所以不能只看 `# `。
    """
    doc_title = (title or "").strip()
    if not doc_title:
        for line in text.split("\n"):
            if line.startswith("# "):
                doc_title = line[2:].strip()
                break
    if not doc_title:
        for section in sections:
            meta = section.metadata or {}
            for key in ("h1", "h2"):
                candidate = str(meta.get(key, "")).strip()
                if candidate and not _SECTION_NO_RE.match(candidate):
                    doc_title = candidate
                    break
            if doc_title:
                break
    if not doc_title:
        doc_title = stem
    return re.sub(r"^\d{2}[-_\s]*", "", doc_title) or stem  # 去掉 01- 这种序号前缀


def _breadcrumb(title: str, h1: str, h2: str, h3: str) -> str:
    return " · ".join(_dedupe_parts((title, h1, h2, h3)))


def split_markdown(
    markdown: str,
    *,
    source_file: str = "",
    title: str = "",
    tenant_id: str = "tenant-demo",
    doc_id: str = "",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """结构感知切分：Markdown 标题优先，超长再递归字符兜底。"""
    text = clean_markdown(markdown)
    if not text.strip():
        return []

    stem = Path(source_file).stem if source_file else "未命名文档"
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON, strip_headers=False
    )
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=RECURSIVE_SEPARATORS,
    )

    sections = header_splitter.split_text(text)
    doc_title = _resolve_title(title, text, sections, stem)
    resolved_doc_id = doc_id or make_doc_id(tenant_id, source_file or stem)

    chunks: list[Chunk] = []
    for section in sections:
        body = section.page_content.strip()
        if not body or _prose_length(body) < MIN_PROSE_CHARS:
            continue
        if any(marker in body for marker in SKIP_MARKERS):
            continue
        meta = section.metadata or {}
        h1 = str(meta.get("h1", "")).strip()
        h2 = str(meta.get("h2", "")).strip()
        h3 = str(meta.get("h3", "")).strip()
        crumb = _breadcrumb(doc_title, h1, h2, h3)
        parts = recursive.split_text(body) if len(body) > chunk_size else [body]
        for part in parts:
            part = part.strip()
            if _prose_length(part) < MIN_PROSE_CHARS:
                continue
            chunks.append(
                Chunk(
                    text=f"【{crumb}】\n{part}" if crumb else part,
                    content=part,
                    metadata={
                        "doc_id": resolved_doc_id,
                        "title": doc_title,
                        "h1": h1,
                        "h2": h2,
                        "h3": h3,
                        "chunk_index": len(chunks),
                        "source_file": source_file or stem,
                        "tenant_id": tenant_id,
                    },
                )
            )
    return chunks


def chunk_stats(chunks: list[Chunk]) -> dict[str, Any]:
    """切分结果体检：块数、字数分布、覆盖了多少个小节。"""
    if not chunks:
        return {"count": 0, "avg_chars": 0, "max_chars": 0, "min_chars": 0, "sections": 0}
    sizes = [len(c.content) for c in chunks]
    sections = {(c.metadata.get("h1", ""), c.metadata.get("h2", ""), c.metadata.get("h3", ""))
                for c in chunks}
    return {
        "count": len(chunks),
        "avg_chars": round(sum(sizes) / len(sizes), 1),
        "max_chars": max(sizes),
        "min_chars": min(sizes),
        "sections": len(sections),
    }