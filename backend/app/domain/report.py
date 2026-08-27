"""ResearchReport structured model + compiler (任务书 §38/§39).

One structured report object per research state; zh-CN and en-US renderers
produce identical numbers, claim ids and citations from that single object
(任务书 §90). Original-language claim/thesis text is never replaced — when
the report language differs from the stored text, the original is shown with
a language marker (§11).
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.report_i18n import tr
from app.domain.evidence import EvidenceType, utc_now

ReportLanguage = str  # "zh-CN" | "en-US"


@dataclass
class ReportSection:
    key: str
    items: list[dict[str, Any]] = field(default_factory=list)
    # each item: {"text_zh": ..., "text_en": ..., "evidence_ids": [...], "numbers": {...}}


@dataclass
class StructuredReport:
    """The single structured research state shape (任务书 §38 fields)."""

    instrument_id: str
    snapshot_id: str
    as_of: datetime
    generated_at: datetime
    sections: dict[str, ReportSection] = field(default_factory=dict)
    citations: list[str] = field(default_factory=list)
    data_quality_notes: list[str] = field(default_factory=list)
    gate_status: str = "not_run"

    def section(self, key: str) -> ReportSection:
        if key not in self.sections:
            self.sections[key] = ReportSection(key=key)
        return self.sections[key]


class ReportRenderer:
    """Renders one StructuredReport into Markdown or HTML in either language."""

    def __init__(self, language: ReportLanguage) -> None:
        self.language = language if language in ("zh-CN", "en-US") else "en-US"

    def _original_marker(self, text_language: str | None) -> str:
        if text_language and text_language != self.language:
            return f" [{tr(self.language, 'label.original_zh')}]" if text_language == "zh-CN" else " [original]"
        return ""

    def render_markdown(self, report: StructuredReport) -> str:
        lines: list[str] = []
        lines.append(f"# {tr(self.language, 'report.title')}: {report.instrument_id}")
        lines.append("")
        lines.append(
            f"- {tr(self.language, 'report.as_of')}: {report.as_of:%Y-%m-%d %H:%M} UTC"
        )
        lines.append(
            f"- {tr(self.language, 'report.generated_at')}: "
            f"{report.generated_at:%Y-%m-%d %H:%M} UTC"
        )
        lines.append(f"- snapshot: `{report.snapshot_id}`")
        lines.append("")

        ordered = [
            "executive_summary", "market_and_capital", "key_theses",
            "corporate_events", "valuation", "scenarios", "bull_bear",
            "risks", "data_quality", "source_manifest", "disclaimer",
        ]
        for key in ordered:
            section = report.sections.get(key)
            if section is None or not section.items:
                lines.append(f"## {tr(self.language, f'section.{key}')}")
                lines.append("")
                lines.append(f"- {tr(self.language, 'label.no_data')}")
                lines.append("")
                continue
            lines.append(f"## {tr(self.language, f'section.{key}')}")
            lines.append("")
            for item in section.items:
                if item.get("is_disclaimer"):
                    lines.append(f"- {tr(self.language, 'disclaimer.text')}")
                    continue
                text = item.get(f"text_{self._lang_suffix()}")
                marker = self._original_marker(item.get("text_language"))
                line = f"- {text}{marker}" if text else f"- {tr(self.language, 'label.no_data')}"
                lines.append(line)
                for ev in item.get("evidence_ids", []):
                    lines.append(f"  - [{ev}]")
            lines.append("")
        return "\n".join(lines)

    def render_html(self, report: StructuredReport) -> str:
        def esc(value: str) -> str:
            return html.escape(value, quote=False)

        parts: list[str] = []
        parts.append(
            f"<h1>{esc(tr(self.language, 'report.title'))}: {esc(report.instrument_id)}</h1>"
        )
        parts.append(
            f"<p>{esc(tr(self.language, 'report.as_of'))}: {report.as_of:%Y-%m-%d %H:%M} UTC · "
            f"{esc(tr(self.language, 'report.generated_at'))}: {report.generated_at:%Y-%m-%d %H:%M} UTC · "
            f"snapshot <code>{esc(report.snapshot_id)}</code></p>"
        )
        ordered = [
            "executive_summary", "market_and_capital", "key_theses",
            "corporate_events", "valuation", "scenarios", "bull_bear",
            "risks", "data_quality", "source_manifest", "disclaimer",
        ]
        for key in ordered:
            section = report.sections.get(key)
            parts.append(f"<h2>{esc(tr(self.language, f'section.{key}'))}</h2>")
            if section is None or not section.items:
                parts.append(f"<p><em>{esc(tr(self.language, 'label.no_data'))}</em></p>")
                continue
            parts.append("<ul>")
            for item in section.items:
                if item.get("is_disclaimer"):
                    parts.append(f"<li>{esc(tr(self.language, 'disclaimer.text'))}</li>")
                    continue
                text = item.get(f"text_{self._lang_suffix()}")
                marker = self._original_marker(item.get("text_language"))
                text = text or tr(self.language, "label.no_data")
                parts.append(f"<li>{esc(text)}{esc(marker)}")
                for ev in item.get("evidence_ids", []):
                    parts.append(f'<ul><li><a class="citation" href="#" data-evidence="{esc(ev)}">[{esc(ev)}]</a></li></ul>')
                parts.append("</li>")
            parts.append("</ul>")
        return "\n".join(parts)

    def _lang_suffix(self) -> str:
        return "zh" if self.language == "zh-CN" else "en"


def numbers_of(markdown: str) -> set[str]:
    """Extract numeric tokens for cross-language consistency assertions."""
    import re

    return set(re.findall(r"\d+(?:\.\d+)?", markdown))
