"""把 docs/kb/src/*.md 渲染成 PDF（供 MinerU 解析入库）。

只支持本项目用到的那一小撮 Markdown：# / ## / ###、段落、- 列表、
| 表格 |、> 提示块、**粗体**、`行内代码`。
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "docs" / "kb" / "src"
PDF_DIR = ROOT / "docs" / "kb" / "pdf"

FONT_BODY = "XlSans"
FONT_BOLD = "XlSans-Bold"
FONT_FILES = [
    (FONT_BODY, r"C:\Windows\Fonts\msyh.ttc"),
    (FONT_BOLD, r"C:\Windows\Fonts\msyhbd.ttc"),
]

INK = colors.HexColor("#1F2733")
INK2 = colors.HexColor("#5A6672")
ACCENT = colors.HexColor("#1F4E79")
RULE = colors.HexColor("#C9D3DE")
HEAD_BG = colors.HexColor("#E8EEF7")
MONO = colors.HexColor("#B03060")

CONTENT_W = A4[0] - 4.4 * cm


class NumberedCanvas:
    """页脚写「第 N 页 / 共 M 页」。"""

    def __new__(cls, *args, **kwargs):
        from reportlab.pdfgen import canvas as _canvas

        class _Canvas(_canvas.Canvas):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self._saved = []

            def showPage(self):
                self._saved.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                total = len(self._saved)
                for state in self._saved:
                    self.__dict__.update(state)
                    self._footer(total)
                    super().showPage()
                super().save()

            def _footer(self, total: int):
                self.setFont(FONT_BODY, 8.5)
                self.setFillColor(INK2)
                page = f"第 {self._pageNumber} 页 / 共 {total} 页"
                self.drawCentredString(A4[0] / 2, 1.35 * cm, page)

        return _Canvas(*args, **kwargs)


def register_fonts() -> None:
    for name, path in FONT_FILES:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))


def inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"`(.+?)`", rf'<font color="{MONO.hexval()[2:]}">\1</font>', out)
    return out


def styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName=FONT_BODY, wordWrap="CJK")
    return {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=22, leading=30,
                                textColor=ACCENT, spaceAfter=10, wordWrap="CJK"),
        "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=14.5, leading=22,
                             textColor=ACCENT, spaceBefore=14, spaceAfter=8, wordWrap="CJK"),
        "h3": ParagraphStyle("h3", fontName=FONT_BOLD, fontSize=11.5, leading=19,
                             textColor=colors.HexColor("#24476F"), spaceBefore=9, spaceAfter=5,
                             wordWrap="CJK"),
        "body": ParagraphStyle("body", fontSize=10.5, leading=19, alignment=TA_JUSTIFY,
                               spaceAfter=7, textColor=INK, **base),
        "bullet": ParagraphStyle("bullet", fontSize=10.5, leading=18, leftIndent=14,
                                 bulletIndent=3, spaceAfter=4, textColor=INK, **base),
        "note": ParagraphStyle("note", fontSize=9, leading=15, textColor=INK2,
                               leftIndent=10, spaceAfter=8, **base),
        "cell": ParagraphStyle("cell", fontSize=9, leading=15, textColor=INK, **base),
        "cellh": ParagraphStyle("cellh", fontName=FONT_BOLD, fontSize=9, leading=15,
                                textColor=ACCENT, alignment=TA_CENTER, wordWrap="CJK"),
        "caption": ParagraphStyle("caption", fontSize=8.5, leading=13, textColor=INK2,
                                  alignment=TA_CENTER, spaceBefore=3, spaceAfter=10, wordWrap="CJK"),
    }


def display_len(text: str) -> int:
    n = 0
    for ch in re.sub(r"[*`]", "", text):
        n += 2 if ord(ch) > 0x2E80 else 1
    return n


def build_table(rows: list[list[str]], st: dict[str, ParagraphStyle]) -> Table:
    header, body = rows[0], rows[1:]
    ncol = len(header)
    widths = [max([display_len(r[i]) for r in rows if i < len(r)] + [4]) for i in range(ncol)]
    weights = [w ** 0.72 for w in widths]
    total = sum(weights)
    col_w = [CONTENT_W * w / total for w in weights]

    data = [[Paragraph(inline(c), st["cellh"]) for c in header]]
    for row in body:
        row = row + [""] * (ncol - len(row))
        data.append([Paragraph(inline(c), st["cell"]) for c in row])

    table = Table(data, colWidths=col_w, repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return table


def parse(md: str, st: dict[str, ParagraphStyle]) -> tuple[str, list]:
    lines = md.splitlines()
    title = "未命名文档"
    flow: list = []
    buf: list[str] = []
    table_rows: list[list[str]] = []

    def flush_para() -> None:
        nonlocal buf
        if buf:
            flow.append(Paragraph(inline("".join(buf)), st["body"]))
            buf = []

    def flush_table() -> None:
        nonlocal table_rows
        if len(table_rows) >= 2:
            flow.append(build_table(table_rows, st))
            flow.append(Spacer(1, 6))
        table_rows = []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("|"):
            flush_para()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            table_rows.append(cells)
            continue
        flush_table()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            flow.append(Paragraph(inline(title), st["title"]))
            flow.append(Spacer(1, 4))
        elif stripped.startswith("## "):
            flush_para()
            flow.append(Paragraph(inline(stripped[3:].strip()), st["h2"]))
        elif stripped.startswith("### "):
            flush_para()
            flow.append(Paragraph(inline(stripped[4:].strip()), st["h3"]))
        elif stripped.startswith("> "):
            flush_para()
            flow.append(Paragraph(inline(stripped[2:].strip()), st["note"]))
        elif stripped.startswith("- "):
            flush_para()
            flow.append(Paragraph(inline(stripped[2:].strip()), st["bullet"],
                                  bulletText="·"))
        else:
            buf.append(stripped)
    flush_table()
    flush_para()
    return title, flow


def render(md_path: Path) -> Path:
    st = styles()
    title, flow = parse(md_path.read_text(encoding="utf-8"), st)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    out = PDF_DIR / f"{md_path.stem}.pdf"

    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.0 * cm,
        title=title, author="星澜科技（虚构示例）",
        subject="Agent 项目知识库演示文档",
    )

    def on_page(canv, _doc):
        canv.saveState()
        canv.setFont(FONT_BODY, 8.5)
        canv.setFillColor(INK2)
        canv.drawString(2.2 * cm, A4[1] - 1.35 * cm, "星澜科技（虚构示例）· 内部制度文档")
        canv.drawRightString(A4[0] - 2.2 * cm, A4[1] - 1.35 * cm, md_path.stem)
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.5)
        canv.line(2.2 * cm, A4[1] - 1.55 * cm, A4[0] - 2.2 * cm, A4[1] - 1.55 * cm)
        canv.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, CONTENT_W,
                  A4[1] - doc.topMargin - doc.bottomMargin, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(flow, canvasmaker=NumberedCanvas)
    return out


def main() -> int:
    register_fonts()
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(SRC_DIR.glob("*.md"))
    if not files:
        print("没有找到 docs/kb/src/*.md")
        return 1
    for md_path in files:
        out = render(md_path)
        print(f"{md_path.name:38} -> {out.relative_to(ROOT)}  ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())