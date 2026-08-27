"""PDF export for reports (任务书 §17/§39).

Uses reportlab's built-in Adobe CJK font (STSong-Light) so Chinese renders
without shipping a font file. PDF is always light-themed for stable
printing/archiving (任务书 §17); content is identical to the on-screen
report and never alters the evidence base.
"""

from __future__ import annotations

import html
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_CJK_FONT = "STSong-Light"
_registered = False


def _ensure_font() -> None:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(UnicodeCIDFont(_CJK_FONT))
        _registered = True


def markdown_to_pdf(markdown: str, title: str) -> bytes:
    """Render the report markdown into a light-themed A4 PDF."""
    _ensure_font()
    buf = io.BytesIO()

    title_style = ParagraphStyle("title", fontName=_CJK_FONT, fontSize=16, leading=22)
    h2_style = ParagraphStyle("h2", fontName=_CJK_FONT, fontSize=13, leading=18, spaceBefore=10)
    body_style = ParagraphStyle("body", fontName=_CJK_FONT, fontSize=10.5, leading=15)
    li_style = ParagraphStyle("li", fontName=_CJK_FONT, fontSize=10.5, leading=15, leftIndent=14)

    doc = SimpleDocTemplate(buf, pagesize=A4, title=title,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    story: list = [Paragraph(_esc(title), title_style), Spacer(1, 8)]

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("## "):
            story.append(Paragraph(_esc(line[3:]), h2_style))
        elif line.startswith("# "):
            story.append(Paragraph(_esc(line[2:]), title_style))
        elif line.startswith("- "):
            story.append(Paragraph("• " + _esc(line[2:]), li_style))
        elif line.startswith("  - ["):  # citation sub-item
            story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;" + _esc(line.strip()), li_style))
        else:
            story.append(Paragraph(_esc(line), body_style))

    doc.build(story)
    return buf.getvalue()


def _esc(text: str) -> str:
    # XML-escape then restore nothing: reportlab paragraphs accept minimal tags.
    return html.escape(text, quote=False)
