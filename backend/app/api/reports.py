"""Reports API (M11): compile from research state, bilingual rendering."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi.responses import Response

from app.core.errors import AppError
from app.db import get_session
from app.services.pdf_export import markdown_to_pdf
from app.services.report_compiler import ReportCompiler
from app.storage.report_repo import ReportRepository

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/compile", status_code=201)
def compile_report(
    snapshot_id: str = Query(min_length=8, max_length=32),
    language: str = Query(default="zh-CN", pattern="^(zh-CN|en-US)$"),
    publish: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> dict:
    """Compile the structured report from one snapshot, gate, and store."""
    compiler = ReportCompiler(session)
    try:
        report = compiler.compile(snapshot_id)
    except KeyError:
        raise AppError("snapshot.not_found", status_code=404) from None

    # P0-07: narrative layer — en-US reports get LLM-translated prose
    if language == "en-US":
        from app.ai.llm_provider import get_llm_provider
        from app.ai.narrative import narrativize_report

        narrativize_report(report, provider=get_llm_provider(), target_language="en-US")

    rendered = compiler.render_and_gate(report, language=language)
    blocked = rendered["gate"]["blocked"]
    published = publish and not blocked

    repo = ReportRepository(session)
    report_id = repo.save(
        instrument_id=report.instrument_id,
        snapshot_id=snapshot_id,
        language=language,
        gate_status=rendered["gate"]["status"],
        published=published,
        markdown=rendered["markdown"],
        html=rendered["html"],
        content={
            "citations": sorted(set(report.citations)),
            "data_quality_notes": report.data_quality_notes,
            "sections": sorted(report.sections.keys()),
            "section_items": {
                key: [
                    {k: v for k, v in item.items() if k != "is_disclaimer"}
                    for item in section.items
                ]
                for key, section in report.sections.items()
            },
        },
    )
    saved = repo.get(report_id)
    assert saved is not None
    return {
        "report": {**saved, "gate": rendered["gate"]},
        "blocked": blocked,
    }


@router.get("")
def list_reports(
    instrument_id: str = Query(min_length=3, max_length=32),
    language: str | None = Query(default=None, pattern="^(zh-CN|en-US)$"),
    session: Session = Depends(get_session),
) -> dict:
    reports = ReportRepository(session).list_for(instrument_id, language=language)
    return {"count": len(reports), "results": reports}


@router.get("/{report_id}")
def get_report(report_id: str, session: Session = Depends(get_session)) -> dict:
    report = ReportRepository(session).get(report_id)
    if report is None:
        raise AppError("report.not_found", status_code=404)
    return {"report": report}


@router.get("/{report_id}/pdf")
def get_report_pdf(report_id: str, session: Session = Depends(get_session)) -> Response:
    """PDF export (light theme, CJK-capable) — content identical to HTML view."""
    report = ReportRepository(session).get(report_id)
    if report is None:
        raise AppError("report.not_found", status_code=404)
    pdf_bytes = markdown_to_pdf(report["markdown"], f"A-Share Research Report: {report['instrument_id']}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{report_id}.pdf"'},
    )
