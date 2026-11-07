"""知识库入库：PDF → Markdown（MinerU）→ chunk（结构感知切分）→ Milvus。

用法（Python 用 .venv）：

  # 1) 只试 MinerU 解析，把 Markdown 存下来看质量
  python -m scripts.ingest_docs --pdf docs/kb/pdf/员工手册.pdf --save-md

  # 2) 解析 + 切分，打印统计与样例 chunk，并把 chunk 落成 jsonl（不入库）
  python -m scripts.ingest_docs --source docs/kb/pdf --out docs/kb/chunks.jsonl

  # 3) 直接切现成的 Markdown（不调用 MinerU）并**写进 Milvus**（日常入库就用这条）
  python -m scripts.ingest_docs --md docs/kb/md --to-milvus

  # 4) 改了 schema / 换 embedding 模型，重建 collection 再入库
  python -m scripts.ingest_docs --md docs/kb/md --to-milvus --force

  # 5) 精准模式（需要 .env 里的 MINERU_API_KEY）
  python -m scripts.ingest_docs --source docs/kb/pdf --mode precision

注意：`--source` 默认扫 docs/kb/pdf。只想切已解析好的 Markdown 时，
把 `--source` 指到一个空目录（或干脆不传 `--md` 之外的参数），避免又把 PDF 重跑一遍 MinerU。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.app.agents import knowledge
from backend.app.agents.rag import pdf_parser
from backend.app.agents.rag.splitter import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    Chunk,
    chunk_stats,
    split_markdown,
)
from backend.app.agents.settings import ROOT_DIR, settings

SUPPORTED_SUFFIXES = {".pdf"}


def _collect(source: Path | None, extra: list[str]) -> list[Path]:
    """收集待处理文件：命令行显式给的 + 目录里扫到的。"""
    files: list[Path] = [Path(p) for p in extra]
    if source and source.exists():
        if source.is_file():
            files.append(source)
        else:
            files.extend(sorted(p for p in source.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES))
    seen, unique = set(), []
    for f in files:
        key = str(f.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _print_chunk(index: int, chunk: Chunk, show: int = 120) -> None:
    print(f"   [{index:02d}] {chunk.citation}  ({len(chunk.content)} 字)")
    preview = chunk.content.replace("\n", " ⏎ ")
    print(f"        {preview[:show]}{'…' if len(preview) > show else ''}")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _chunks_from_markdown(
    markdown: str,
    *,
    source_file: str,
    title: str,
    tenant_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    return split_markdown(
        markdown,
        source_file=source_file,
        title=title,
        tenant_id=tenant_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="PDF/Markdown → chunk → Milvus（知识库入库）")
    parser.add_argument("--source", default=None, help="PDF 目录（默认 settings.kb_source_dir；给了 --md 就不扫）")
    parser.add_argument("--pdf", nargs="*", default=[], help="显式指定 PDF 文件（可多个）")
    parser.add_argument("--md", nargs="*", default=[], help="直接切现成 Markdown（跳过 MinerU）")
    parser.add_argument("--mode", default=None, choices=["flash", "precision"], help="MinerU 解析模式")
    parser.add_argument("--ocr", action="store_true", help="扫描件才需要（更慢）")
    parser.add_argument("--tenant", default="tenant-demo", help="租户 id")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    parser.add_argument("--out", default="", help="把 chunk 写成 jsonl 的路径（可选）")
    parser.add_argument("--save-md", action="store_true", help="把 MinerU 解析出的 Markdown 存到 docs/kb/md/")
    parser.add_argument("--to-milvus", action="store_true", help="写入 Milvus（入库）")
    parser.add_argument("--force", action="store_true", help="配合 --to-milvus：先 drop 重建 collection")
    parser.add_argument("--limit", type=int, default=0, help="最多处理几个文件（调试用）")
    args = parser.parse_args(argv)

    md_files: list[Path] = []
    for raw in args.md:
        candidate = Path(raw)
        if candidate.is_dir():
            md_files.extend(sorted(candidate.rglob("*.md")))
        else:
            md_files.append(candidate)
    # 给了 --md 就只切 Markdown；否则扫 PDF 目录（避免顺手把 7 份 PDF 又跑一遍 MinerU）
    source_dir = Path(args.source) if args.source else (None if md_files else settings.kb_source_dir)
    pdf_files = _collect(source_dir, args.pdf) if source_dir or args.pdf else []
    if args.limit:
        pdf_files = pdf_files[: args.limit]

    if not md_files and not pdf_files:
        print(f"[x] 没找到文档：{source_dir or '未指定目录'} 下没有 PDF，也没有传 --pdf / --md")
        print("    先把公开制度 PDF 放进 docs/kb/pdf/，或用 --md 直接切已解析好的 Markdown")
        return 2

    print("=" * 78)
    print(f"入库参数：租户={args.tenant}  chunk={args.chunk_size}/{args.chunk_overlap}  "
          f"MinerU={args.mode or settings.mineru_mode}  token={'已配' if settings.mineru_api_key else '未配（只能用 flash）'}")
    print(f"待处理：PDF {len(pdf_files)} 个，Markdown {len(md_files)} 个")
    print("=" * 78)

    all_chunks: list[Chunk] = []

    # ---------- Markdown 直接切 ----------
    for path in md_files:
        markdown = path.read_text(encoding="utf-8")
        chunks = _chunks_from_markdown(
            markdown,
            source_file=path.name,
            title="",
            tenant_id=args.tenant,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"\n[md] {path.name}  →  {chunk_stats(chunks)}")
        for i, chunk in enumerate(chunks[:5]):
            _print_chunk(i, chunk)
        all_chunks.extend(chunks)

    # ---------- PDF 走 MinerU ----------
    for path in pdf_files:
        print(f"\n[pdf] {path.name}  解析中（MinerU {args.mode or settings.mineru_mode}）…")
        try:
            parsed = pdf_parser.parse(path, mode=args.mode, ocr=(True if args.ocr else None))
        except pdf_parser.MinerUUnavailable as exc:
            print(f"   [x] 解析失败：{exc}")
            continue

        print(f"   ok：{parsed.elapsed_s}s，markdown {len(parsed.markdown)} 字，图片 {parsed.image_count} 张"
              f"{'，task_id=' + parsed.task_id if parsed.task_id else ''}")
        print("   markdown 前 6 行：")
        for line in parsed.markdown.split("\n")[:6]:
            print(f"     | {line[:90]}")

        if args.save_md:
            out_md = ROOT_DIR / "docs" / "kb" / "md" / f"{path.stem}.md"
            out_md.parent.mkdir(parents=True, exist_ok=True)
            out_md.write_text(parsed.markdown, encoding="utf-8")
            print(f"   markdown 已存：{out_md}")

        chunks = _chunks_from_markdown(
            parsed.markdown,
            source_file=path.name,
            title="",
            tenant_id=args.tenant,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"   切分：{chunk_stats(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            _print_chunk(i, chunk)
        all_chunks.extend(chunks)

    print("\n" + "=" * 78)
    print(f"合计 chunk：{len(all_chunks)}")

    if args.out and all_chunks:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT_DIR / out
        _write_jsonl(out, [{"text": c.text, "content": c.content, **c.metadata} for c in all_chunks])
        print(f"chunk 已写：{out}（{len(all_chunks)} 行）")

    if args.to_milvus and all_chunks:
        print(f"\n写入 Milvus（集合 {settings.milvus_collection}，租户 {args.tenant}）…")
        try:
            count = knowledge.ingest(all_chunks, tenant_id=args.tenant, force=args.force)
        except Exception as exc:  # noqa: BLE001
            print(f"[x] 入库失败：{type(exc).__name__}: {exc}")
            return 2
        stats = knowledge.health()
        print(f"入库完成：{count} 条；collection 当前 {stats['rows']} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())