import { newResearchContext } from "../../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../../shared/handoff";

/**
 * 产业研究三视图数据契约（Guanlan Direct Port G2，方案 §7-§12/§24）。
 * 数据全部来自 GET /views/industry/*（真实证据组装的只读投影）；
 * 驱动/传导/叙事/站位等尚无证据源的象限为 null/[] + disclosures 显形。
 */

export interface IndustrySegment {
  segment_id: string;
  name: string;
  level: number;
  is_current: boolean;
  definition: string | null;
  momentum: number | null;
  temperature: number | null;
  research_count: number | null;
  stars: number;
  evidence_count?: number;
}

export interface RelatedInstrument {
  instrument_id: string;
  name: string;
  code: string | null;
  basis: string;
}

export interface GlobalTheme {
  title: string;
  topic: string | null;
  mentions_official_body: boolean;
  official_bodies: string[];
  summary: string;
  available_time: string;
  evidence_id: string;
}

export interface MacroIndicator {
  code: string;
  name: string;
  value: number | null;
  change: number | null;
  market_time: string;
  available_time: string;
}

export interface IndustryView {
  instrument: { instrument_id: string; name: string | null; code: string | null };
  map_id: string | null;
  context_snapshot_id: string | null;
  industry_label: string | null;
  chain_levels: string[];
  segments: IndustrySegment[];
  related_instruments: RelatedInstrument[];
  global: {
    axes: Array<{ key: string; greek: string }>;
    themes: GlobalTheme[];
    indicators: MacroIndicator[];
    positions: unknown[];
    disclosures: Record<string, string>;
  };
  as_of: string | null;
  reports: Array<{
    report_id: string;
    name: string | null;
    code: string | null;
    gate_status: string;
    created_at: string | null;
  }>;
  disclosures: Record<string, string>;
}

export interface SegmentView {
  instrument: { instrument_id: string; name: string | null; code: string | null };
  segment: IndustrySegment | null;
  industry_label: string | null;
  related_instruments: RelatedInstrument[];
  evidence: Array<{
    evidence_id: string;
    title: string;
    summary: string;
    available_time: string | null;
  }>;
  reports: IndustryView["reports"];
  disclosures: Record<string, string>;
  as_of: string | null;
}

export async function fetchIndustryView(instrumentId: string): Promise<IndustryView> {
  const resp = await fetch(`/api/v1/views/industry/${encodeURIComponent(instrumentId)}`);
  if (!resp.ok) throw new Error("industry_map.not_collected");
  return ((await resp.json()) as { view: IndustryView }).view;
}

export async function fetchSegmentView(
  instrumentId: string,
  segmentId: string,
): Promise<SegmentView> {
  const resp = await fetch(
    `/api/v1/views/industry/${encodeURIComponent(instrumentId)}/segment/${encodeURIComponent(segmentId)}`,
  );
  if (!resp.ok) throw new Error("industry_map.segment_not_found");
  return ((await resp.json()) as { view: SegmentView }).view;
}

/** open_with_context 信封（Phase H 行为保留：视图 → 工作台上下文不丢失）。 */
export async function openWorkspaceWith(
  sourceModule: string,
  domainType: string,
  domainId: string,
  instrumentId: string,
): Promise<string> {
  const artifact = await artifactByDomain(domainType, domainId);
  if (artifact == null) {
    throw new Error("artifact.not_found");
  }
  const envelope = await recordHandoff({
    source_module: sourceModule,
    target_module: "workspace",
    action: "open_with_context",
    artifact_ids: [artifact.artifact_id],
    context: newResearchContext({
      primary_instrument_id: instrumentId,
      instrument_ids: [instrumentId],
    }),
    message: `${sourceModule} → open_with_context`,
  });
  return handoffPath(`/instrument/${instrumentId}`, envelope);
}
