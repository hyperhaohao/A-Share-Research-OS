/**
 * G1 产业链图谱视图（观澜语义迁移任务书 §G1 UI）：
 * 节点（环节 stage 顺序）+ 边（relation_type/方向/时滞/强度/状态）+
 * 传导机制 + 证据入口 + 公司链上位置。
 * 数据来自 /industry-graph/*（真实图谱域；行业分类树不再是产业链）。
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Panel } from "../../ui/guanlan";

interface GraphChain {
  chain_id: string;
  name: string;
  description: string;
  version: number;
}

interface GraphSegment {
  segment_id: string;
  chain_id: string;
  name: string;
  stage_order: number;
  description: string;
}

interface GraphEdge {
  edge_id: string;
  chain_id: string;
  source_segment_id: string;
  target_segment_id: string;
  relation_type: string;
  transmission_metric: string;
  direction: string;
  lag_min_days: number;
  lag_max_days: number;
  strength: number;
  confidence_level: string;
  status: string;
  evidence: Array<{ evidence_id: string; stance: string; available_time: string | null }>;
}

interface GraphPosition {
  position_id: string;
  instrument_id: string;
  chain_id: string;
  segment_id: string;
  role: string;
  revenue_exposure_pct: number | null;
  profit_exposure_pct: number | null;
  capacity_note: string;
}

interface ChainGraph {
  chain: GraphChain;
  segments: GraphSegment[];
  edges: GraphEdge[];
  positions: GraphPosition[];
  as_of: string;
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("network.unreachable");
  return resp.json();
}

export function IndustryGraphView({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const [chainId, setChainId] = useState<string | null>(null);

  const chainsQuery = useQuery({
    queryKey: ["industry-graph-chains"],
    queryFn: () =>
      fetchJson<{ results: GraphChain[] }>("/api/v1/industry-graph/chains"),
  });
  const chains = chainsQuery.data?.results ?? [];
  const activeChainId = chainId ?? chains[0]?.chain_id ?? null;

  const graphQuery = useQuery({
    queryKey: ["industry-graph", activeChainId],
    enabled: activeChainId != null,
    queryFn: () =>
      fetchJson<ChainGraph>(`/api/v1/industry-graph/chains/${activeChainId}/graph`),
  });
  const graph = graphQuery.data;

  const positionsQuery = useQuery({
    queryKey: ["industry-graph-positions", instrumentId],
    queryFn: () =>
      fetchJson<{ results: GraphPosition[] }>(
        `/api/v1/industry-graph/instruments/${encodeURIComponent(instrumentId)}/positions`,
      ),
  });
  const positions = (positionsQuery.data?.results ?? []).filter(
    (p) => activeChainId == null || p.chain_id === activeChainId,
  );

  const segmentName = (id: string): string =>
    graph?.segments.find((s) => s.segment_id === id)?.name ?? id;

  return (
    <div data-testid="industry-graph-view">
      {chains.length > 1 && (
        <div className="rc-filter" role="tablist" aria-label={t("industryWs.graphChains")}>
          {chains.map((c) => (
            <button
              key={c.chain_id}
              type="button"
              role="tab"
              aria-selected={c.chain_id === activeChainId}
              className={`gl-button${c.chain_id === activeChainId ? " gl-button-primary" : ""}`}
              onClick={() => setChainId(c.chain_id)}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}

      {graph == null ? (
        <Panel title={t("industryWs.graphTitle")}>
          <p className="secondary">{t("industryWs.graphEmpty")}</p>
          <p className="secondary mono">{t("industryWs.graphSeedHint")}</p>
        </Panel>
      ) : (
        <>
          <Panel title={`${t("industryWs.graphSegments")} · ${graph.chain.name}`}>
            <div className="ig-segment-row" data-testid="graph-segments">
              {graph.segments.map((s) => {
                const here = positions.filter((p) => p.segment_id === s.segment_id);
                return (
                  <div key={s.segment_id} className="ig-segment" title={s.description}>
                    <span className="ig-segment-order mono">{s.stage_order + 1}</span>
                    <span className="ig-segment-name">{s.name}</span>
                    {here.length > 0 && (
                      <span className="secondary mono ig-segment-pos">
                        {here.length} {t("industryWs.graphCompanies")}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title={t("industryWs.graphEdges")} hint={`${graph.edges.length}`}>
            <ul className="watch-list" data-testid="graph-edges">
              {graph.edges.length === 0 && <p className="secondary">—</p>}
              {graph.edges.map((e) => (
                <li key={e.edge_id} className="result-row ig-edge" data-testid="graph-edge">
                  <span className="ig-edge-path">
                    {segmentName(e.source_segment_id)}
                    <span
                      className={`ig-edge-dir ${e.direction === "negative" ? "down" : "up"}`}
                      aria-label={e.direction}
                    >
                      {e.direction === "negative" ? "↛" : "→"}
                    </span>
                    {segmentName(e.target_segment_id)}
                  </span>
                  <span className="mono secondary ig-edge-relation">{e.relation_type}</span>
                  <span className="secondary ig-edge-metric" title={e.transmission_metric}>
                    {e.transmission_metric || "—"}
                  </span>
                  <span className="secondary mono">
                    {e.lag_min_days}–{e.lag_max_days}d
                  </span>
                  <span
                    className={`mono ${
                      e.status === "active"
                        ? "status-ok"
                        : e.status === "degraded"
                          ? "status-error"
                          : "secondary"
                    }`}
                    data-testid="graph-edge-status"
                  >
                    {t(`industryWs.edgeStatus.${e.status}`, { defaultValue: e.status })}
                  </span>
                  <span className="ig-edge-evidence" data-testid="graph-edge-evidence">
                    {(e.evidence ?? []).map((ev) => (
                      <span key={ev.evidence_id} className="mono secondary">
                        {ev.evidence_id.slice(0, 14)}
                        {ev.stance === "contrary" ? "⇄" : ""}
                      </span>
                    ))}
                    {(e.evidence ?? []).length === 0 && (
                      <span className="secondary">{t("industryWs.noEdgeEvidence")}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title={t("industryWs.graphPositions")}>
            <ul className="watch-list" data-testid="graph-positions">
              {positions.length === 0 && (
                <p className="secondary">{t("industryWs.noPositions")}</p>
              )}
              {positions.map((p) => (
                <li key={p.position_id} className="result-row">
                  <span>{segmentName(p.segment_id)}</span>
                  <span className="mono secondary">{p.role}</span>
                  <span className="secondary mono">
                    {p.revenue_exposure_pct != null
                      ? `${t("industryWs.revenueExposure")} ${p.revenue_exposure_pct}%`
                      : "—"}
                  </span>
                  <span className="secondary ig-pos-note">{p.capacity_note?.slice(0, 60)}</span>
                </li>
              ))}
            </ul>
            <p className="secondary mono ig-as-of">
              as_of: {graph.as_of?.slice(0, 19)} · {t("industryWs.graphReplayable")}
            </p>
          </Panel>
        </>
      )}
    </div>
  );
}
