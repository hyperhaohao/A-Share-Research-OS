"""Evidence collection service: SourceResult → EvidenceRecord + Manifest.

This is the disciplined entry point from the outside world into the research
fact base (任务书 §8: Source before Evidence). Collection is idempotent —
the same real-world fact ingested twice yields one stored evidence atom.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.evidence import (
    AuthorityLevel,
    EvidenceRecord,
    EvidenceType,
    FactStatus,
    SourceManifest,
)
from app.sources.base import SourceRequest, SourceResult, SourceStatus, utc_now
from app.sources.runtime import SourceRuntime, get_runtime
from app.storage.repository import EvidenceRepository

# Provider/truth mapping for quote data: exchanges are the primary source,
# key-free redistributors carry it onward. A quote is a confirmed market fact.
_QUOTE_MAPPING = (EvidenceType.MARKET_QUOTE, FactStatus.CONFIRMED_FACT, AuthorityLevel.B2)


def evidence_type_for(capability: str) -> tuple[EvidenceType, FactStatus, AuthorityLevel]:
    mapping = {
        "market_data": _QUOTE_MAPPING,
    }
    return mapping.get(capability, (EvidenceType.NEWS, FactStatus.MEDIA_REPORT, AuthorityLevel.C2))


@dataclass
class CollectionOutcome:
    manifest: SourceManifest
    evidence: list[EvidenceRecord]
    created_ids: list[str]
    deduped_count: int


def collect_capability_evidence(
    instrument_id: str,
    capability: str,
    *,
    runtime: SourceRuntime | None = None,
    repo: EvidenceRepository,
    fresh: bool = False,
) -> CollectionOutcome:
    """Resolve a capability through the source layer and store evidence.

    Failure semantics: a failed collection still records its SourceManifest
    (with the final failure status) so the UI can show *why* nothing is there
    — a failed source is never presented as "no data" (任务书 §20).

    ``fresh=True`` bypasses the TTL cache — used by Refresh flows (任务书 §42)
    whose entire purpose is to re-check against new source data.
    """
    rt = runtime or get_runtime()
    request = SourceRequest(capability=capability, instrument_id=instrument_id, as_of=utc_now())
    if fresh:
        result = rt.registry.resolve(request)
    else:
        result = rt.resolve_cached(request)
    return store_result_as_evidence(result, repo=repo)


def store_result_as_evidence(
    result: SourceResult,
    *,
    repo: EvidenceRepository,
) -> CollectionOutcome:
    type_mapping = evidence_type_for(result.capability)
    evidence: list[EvidenceRecord] = []
    created_ids: list[str] = []
    deduped = 0

    chain = result.metadata.get("fallback_chain") or [result.source]
    providers_attempted = tuple(
        {"source": source, "status": result.status.value} for source in chain
    )
    subject = result.records[0].subject if result.records else (result.metadata.get("instrument_id") or "")
    manifest = SourceManifest(
        instrument_id=subject,
        capability=result.capability,
        requested_as_of=result.as_of,
        providers_attempted=providers_attempted,
        final_status=result.status.value,
        final_source=result.source if result.is_success() else None,
        from_cache=bool(result.metadata.get("from_cache", False)),
    )

    if result.is_success():
        for record in result.records:
            payload = dict(record.payload)
            ev_type, fact_status, authority = type_mapping
            item = EvidenceRecord(
                instrument_id=record.subject,
                evidence_type=ev_type,
                title=f"{record.subject} {ev_type.value} @ {record.available_time:%Y-%m-%d %H:%M}",
                summary=payload.get("summary") or _summarize(ev_type, payload),
                excerpt=None,
                source=result.source,
                source_type=_source_type_for(result.source),
                source_url=record.source_uri,
                source_document_id=None,
                authority_level=authority,
                fact_status=fact_status,
                event_time=record.event_time or record.available_time,
                available_time=record.available_time,
                ingested_time=utc_now(),
                revision_time=record.available_time,
                confidence=1.0,
                metadata=payload,
            )
            evidence_id, created = repo.save(item, manifest_id=manifest.manifest_id)
            if created:
                created_ids.append(evidence_id)
            else:
                deduped += 1
            evidence.append(item)

    manifest.evidence_ids = tuple(created_ids)
    repo.save_manifest(manifest)
    return CollectionOutcome(
        manifest=manifest, evidence=evidence, created_ids=created_ids, deduped_count=deduped
    )


def _summarize(evidence_type: EvidenceType, payload: dict) -> str:
    if evidence_type is EvidenceType.MARKET_QUOTE:
        parts = [f"price={payload.get('price')}", f"change_pct={payload.get('change_pct')}"]
        if payload.get("total_market_cap_yuan") is not None:
            parts.append(f"mcap={payload['total_market_cap_yuan']:.0f}")
        return "market quote: " + ", ".join(parts)
    return f"{evidence_type.value}: {payload}"


def _source_type_for(source_id: str) -> str:
    if source_id == "tencent_quote":
        return "market_data_redistributor"
    return "external_source"
