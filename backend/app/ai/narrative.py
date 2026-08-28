"""Narrative Layer (整改 R3.4): bilingual report prose.

The structured research state is shared across languages (evidence ids,
claim ids, thesis ids, numbers, snapshot, run). This layer adds *narrative*
text: when an LLM is configured, zh-CN original prose is translated into
en-US so English reports stop reusing Chinese text verbatim; citations still
point at the original evidence and originals are never overwritten.

Without an LLM the deterministic fallback keeps the stored original text
with a language marker — honest, just not translated.
"""

from __future__ import annotations

import json

from app.ai.llm_provider import BaseLLMProvider
from app.domain.report import StructuredReport


def _translatable(report: StructuredReport) -> list[tuple[str, int, str]]:
    """(section key, item index, zh text) for items whose only stored prose
    is Chinese and which carry no generated symmetric text."""
    targets: list[tuple[str, int, str]] = []
    for key, section in report.sections.items():
        for idx, item in enumerate(section.items):
            zh = item.get("text_zh")
            en = item.get("text_en")
            if item.get("is_disclaimer"):
                continue
            if zh and not en and item.get("text_language") == "zh-CN":
                targets.append((key, idx, zh))
    return targets


def _batch_prompt(pairs: list[tuple[str, str]]) -> str:
    lines = [
        "Translate each Chinese research note into concise English. "
        "Keep numbers, dates and ids exactly as-is. Do not add facts.",
        "Return a single JSON object mapping each index to the English text.",
        "",
    ]
    for idx, zh in pairs:
        lines.append(f"{idx}: {zh}")
    return "\n".join(lines)


def narrativize_report(
    report: StructuredReport,
    *,
    provider: BaseLLMProvider | None,
    target_language: str = "en-US",
) -> dict:
    """Fill ``text_en`` for Chinese-only items. Returns a summary:
    {"translated": n, "fallback": m, "kind": "llm"|"deterministic"}.

    Deterministic fallback: item gets a language marker instead of a fake
    translation — no fabricated prose.
    """
    if target_language != "en-US":
        return {"translated": 0, "fallback": 0, "kind": "skipped"}

    targets = _translatable(report)
    if not targets:
        return {"translated": 0, "fallback": 0, "kind": "noop"}

    if provider is None:
        for key, idx, _zh in targets:
            item = report.sections[key].items[idx]
            item["text_en"] = item["text_zh"]
            item["text_language"] = "zh-CN"  # marker: original preserved
        return {"translated": 0, "fallback": len(targets), "kind": "deterministic"}

    # chunk to keep prompts bounded
    translated = 0
    chunk_size = 8
    for start in range(0, len(targets), chunk_size):
        chunk = targets[start : start + chunk_size]
        prompt = _batch_prompt([(f"{key}#{idx}", zh) for key, idx, zh in chunk])
        schema_hint = '{"<key>#<idx>": "english text", ...}'
        try:
            mapping = provider.generate_structured(
                prompt, schema_hint=schema_hint,
                system="Financial research translator. Never add or alter facts.",
            )
        except Exception:  # noqa: BLE001 — LLM failure falls back to marker
            for key, idx, _zh in chunk:
                item = report.sections[key].items[idx]
                item["text_en"] = item["text_zh"]
                item["text_language"] = "zh-CN"
            continue
        for key, idx, zh in chunk:
            item = report.sections[key].items[idx]
            en = (mapping or {}).get(f"{key}#{idx}")
            if isinstance(en, str) and en.strip():
                item["text_en"] = en.strip()
                item["text_language"] = None  # generated translation
                translated += 1
            else:
                item["text_en"] = zh
                item["text_language"] = "zh-CN"
    return {"translated": translated, "fallback": len(targets) - translated, "kind": "llm"}


def narrative_summary(report: StructuredReport) -> dict:
    return json.dumps({"sections": list(report.sections.keys())}, ensure_ascii=False)
