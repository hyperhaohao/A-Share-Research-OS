import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TimelineTab } from "../components/ResearchVisuals";
import { FinancialsTab, ThesisTab, ValuationTab, WorkspaceReportsTab } from "../components/WorkspaceTabs";
import { CopilotSidebar } from "../components/CopilotSidebar";
import { FlowGraphTab } from "../components/FlowGraph";

interface InstrumentProfile {
  instrument_id: string;
  code: string;
  name: string;
  exchange: string;
  board: string;
  market: string;
  industry: string | null;
  sector: string | null;
  market_cap: number | null;
  data_availability: string[];
}

interface EvidenceItem {
  evidence_id: string;
  evidence_type: string;
  title: string;
  source: string;
  available_time: string;
  metadata: Record<string, unknown>;
}

interface PredictionItem {
  prediction_id: string;
  horizon: string;
  expected_direction: string;
  validation?: { instrument_return_pct: number; direction_correct: boolean | null };
}

async function fetchInstrument(id: string): Promise<InstrumentProfile> {
  const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error("instrument.not_found");
  const body = await resp.json();
  return body.instrument;
}

async function fetchEvidence(id: string): Promise<EvidenceItem[]> {
  const resp = await fetch(`/api/v1/evidence?instrument_id=${encodeURIComponent(id)}`);
  if (!resp.ok) return [];
  const body = await resp.json();
  return body.results;
}

async function fetchPredictions(id: string): Promise<PredictionItem[]> {
  const resp = await fetch(`/api/v1/predictions?instrument_id=${encodeURIComponent(id)}`);
  if (!resp.ok) return [];
  const body = await resp.json();
  return body.results;
}

const PRIMARY_TABS = ["overview", "research", "fundamentals", "evidence", "artifacts"] as const;
type PrimaryTab = (typeof PRIMARY_TABS)[number];

const SUB_TABS: Record<Exclude<PrimaryTab, "overview">, Array<{ key: string }>> = {
  research: [{ key: "timeline" }, { key: "graph" }, { key: "thesis" }],
  fundamentals: [{ key: "financials" }, { key: "valuation" }],
  evidence: [{ key: "evidence" }],
  artifacts: [{ key: "reports" }, { key: "predictions" }],
};

/** Stock Workspace (任务书 §58): header + Overview/Timeline/Graph/Evidence/Predictions. */
export function InstrumentWorkspacePage() {
  const { instrumentId = "" } = useParams();
  const { t } = useTranslation();
  const [primaryTab, setPrimaryTab] = useState<PrimaryTab>("overview");
  const [subTab, setSubTab] = useState("timeline");

  const instrumentQuery = useQuery({
    queryKey: ["instrument", instrumentId],
    queryFn: () => fetchInstrument(instrumentId),
    retry: false,
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence", instrumentId],
    queryFn: () => fetchEvidence(instrumentId),
  });
  const predictionsQuery = useQuery({
    queryKey: ["predictions", instrumentId],
    queryFn: () => fetchPredictions(instrumentId),
  });

  if (instrumentQuery.isError) {
    return (
      <main className="page">
        <p className="status-error">{t("watchlist.empty")}</p>
      </main>
    );
  }

  const inst = instrumentQuery.data;
  const evidence = evidenceQuery.data ?? [];
  const latestQuote = [...evidence]
    .filter((e) => e.evidence_type === "market_quote")
    .sort((a, b) => (a.available_time < b.available_time ? 1 : -1))[0];

  return (
    <main className="page" data-testid="workspace-page">
      <header className="workspace-header">
        <h1 data-testid="workspace-name">{inst?.name ?? instrumentId}</h1>
        <span className="mono secondary">
          {inst ? `${inst.exchange}:${inst.code} · ${inst.market} · ${inst.board}` : instrumentId}
        </span>
        <span className="secondary">{inst?.industry ?? t("label.missing")}</span>
        <Link
          className="control-btn"
          data-testid="workspace-industry-map"
          to={`/industry-map/${instrumentId}`}
        >
          {t("industryMap.title")}
        </Link>
        <Link
          className="control-btn"
          data-testid="workspace-global-context"
          to={`/global-context/${instrumentId}`}
        >
          {t("globalContext.title")}
        </Link>
      </header>

      <div className="workspace-body">
      <div className="workspace-main">
      <div className="workspace-tabs" role="tablist" aria-label={t("workspace.tabs")}>
        {PRIMARY_TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={primaryTab === key}
            className={primaryTab === key ? "control-btn active" : "control-btn"}
            onClick={() => {
              setPrimaryTab(key);
              setSubTab(
                key === "overview" ? "timeline" : SUB_TABS[key as Exclude<PrimaryTab, "overview">][0].key,
              );
            }}
          >
            {t(`workspace.primaryTab.${key}`)}
          </button>
        ))}
      </div>

      {primaryTab !== "overview" && (
        <div className="workspace-tabs" role="tablist" aria-label={t("workspace.subtabs")}>
          {SUB_TABS[primaryTab as Exclude<PrimaryTab, "overview">].map((s) => (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={subTab === s.key}
              className={subTab === s.key ? "control-btn active" : "control-btn"}
              onClick={() => setSubTab(s.key)}
            >
              {t(`workspace.tab.${s.key}`)}
            </button>
          ))}
        </div>
      )}

      {primaryTab === "overview" && <OverviewGrid instrumentId={instrumentId} />}

      {primaryTab === "research" && (
        <section className="card">
          <h2>{t("workspace.market")}</h2>
          {latestQuote ? (
            <p className="mono">
              {String(latestQuote.metadata.price ?? "—")}
              <span className="quote-up">
                {" "}
                {String(latestQuote.metadata.change_pct ?? "")}%
              </span>
            </p>
          ) : (
            <p className="secondary">{t("label.no_data")}</p>
          )}
          <p className="secondary">
            {t("workspace.evidenceCount", { count: evidence.length })}
          </p>
        </section>
      )}

      {primaryTab === "research" && subTab === "timeline" && <TimelineTab instrumentId={instrumentId} />}
      {primaryTab === "research" && subTab === "graph" && <FlowGraphTab instrumentId={instrumentId} />}
      {primaryTab === "research" && subTab === "thesis" && <ThesisTab instrumentId={instrumentId} />}
      {primaryTab === "fundamentals" && subTab === "financials" && (
        <FinancialsTab instrumentId={instrumentId} />
      )}
      {primaryTab === "fundamentals" && subTab === "valuation" && (
        <ValuationTab instrumentId={instrumentId} />
      )}
      {primaryTab === "artifacts" && subTab === "reports" && (
        <WorkspaceReportsTab instrumentId={instrumentId} />
      )}

      {primaryTab === "evidence" && (
        <section className="card">
          <h2>{t("workspace.evidence")}</h2>
          {evidence.length === 0 && <p className="secondary">{t("label.no_data")}</p>}
          <ul className="watch-list">
            {evidence.slice(0, 20).map((e) => (
              <li key={e.evidence_id} className="result-row">
                <span className="mono secondary">{e.evidence_type}</span>
                <span>{e.title}</span>
                <span className="mono secondary">{e.source}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {primaryTab === "artifacts" && subTab === "predictions" && (
        <section className="card">
          <h2>{t("workspace.predictions")}</h2>
          {predictionsQuery.data?.length === 0 && (
            <p className="secondary">{t("label.no_data")}</p>
          )}
          <ul className="watch-list">
            {(predictionsQuery.data ?? []).map((p) => (
              <li key={p.prediction_id} className="result-row">
                <span className="mono">{p.horizon}</span>
                <span>{t(`workspace.direction.${p.expected_direction}`)}</span>
                {p.validation && (
                  <span className="mono secondary">
                    {p.validation.instrument_return_pct}%
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      </div>{/* /workspace-main */}

      <CopilotSidebar instrumentId={instrumentId} />
      </div>{/* /workspace-body */}

      <p>
        <Link to="/" className="secondary">
          ← {t("home.title")}
        </Link>
      </p>
    </main>
  );
}

/** Overview 网格（§16）：来自 InstrumentOverviewView 的 L1/L2。 */
interface OverviewView {
  instrument: { instrument_id: string; code: string; name: string | null } | null;
  quote: { price: number; change_pct: number | null; quote_time: string | null } | null;
  research: { judgment: string | null; confidence: number | null; thesis_title: string | null };
  catalysts: string[];
  risks: string[];
  report: { report_id: string; created_at: string | null } | null;
  prediction: { prediction_id: string; horizon: string; expected_direction: string; validated: boolean; due_at: string | null } | null;
  monitor: { monitor_id: string; enabled: boolean; next_run_at: string | null } | null;
  valuation: {
    current_price: number | null;
    as_of: string | null;
    methods: Array<{ method: string; implied_price: number; upside_pct: number | null }>;
  } | null;
  latest_changes: Array<{ evidence_type: string; title: string; available_time: string }>;
  data_quality: {
    evidence_count: number;
    source_kinds: number;
    quality_score: string;
    capability_breakdown: Record<string, number>;
  };
}

function OverviewGrid({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const ovQuery = useQuery({
    queryKey: ["instrument-overview", instrumentId],
    enabled: instrumentId !== "",
    queryFn: async (): Promise<OverviewView> => {
      const resp = await fetch(
        `/api/v1/views/instruments/${encodeURIComponent(instrumentId)}/overview`,
      );
      if (!resp.ok) throw new Error("instrument.not_found");
      const body = await resp.json();
      return body.overview;
    },
  });
  const ov = ovQuery.data;
  if (ovQuery.isPending) return <p className="secondary">{t("common.loading")}</p>;
  if (ovQuery.isError || !ov) return <p className="secondary">{t("label.no_data")}</p>;

  return (
    <div className="overview-grid" data-testid="workspace-overview">
      <section className="card">
        <h2>{t("workspace.overviewStance")}</h2>
        <p>
          {ov.research.judgment ? t(`workspace.direction.${ov.research.judgment}`) : "—"}
          {ov.research.confidence != null ? ` · ${Math.round(ov.research.confidence * 100)}%` : ""}
        </p>
        {ov.research.thesis_title && <p className="secondary">{ov.research.thesis_title}</p>}
      </section>
      <section className="card">
        <h2>{t("workspace.overviewValuation")}</h2>
        {ov.valuation ? (
          <>
            <p className="mono">
              {t("workspace.currentPrice")}: {ov.valuation.current_price}
            </p>
            {ov.valuation.methods.map((m) => (
              <p key={m.method} className="mono secondary">
                {m.method}: {m.implied_price} ({m.upside_pct != null ? `${m.upside_pct >= 0 ? "+" : ""}${m.upside_pct}%` : "—"})
              </p>
            ))}
          </>
        ) : (
          <p className="secondary">{t("label.no_data")}</p>
        )}
      </section>
      <section className="card">
        <h2>{t("workspace.overviewCatalysts")}</h2>
        {ov.catalysts.length ? (
          <ul className="watch-list">
            {ov.catalysts.map((c) => (
              <li key={c}>• {c}</li>
            ))}
          </ul>
        ) : (
          <p className="secondary">—</p>
        )}
      </section>
      <section className="card">
        <h2>{t("workspace.overviewRisks")}</h2>
        {ov.risks.length ? (
          <ul className="watch-list">
            {ov.risks.map((r) => (
              <li key={r}>• {r}</li>
            ))}
          </ul>
        ) : (
          <p className="secondary">—</p>
        )}
      </section>
      <section className="card">
        <h2>{t("workspace.overviewLatest")}</h2>
        {ov.latest_changes.length === 0 ? (
          <p className="secondary">—</p>
        ) : (
          <ul className="watch-list">
            {ov.latest_changes.map((c, i) => (
              <li className="result-row" key={i}>
                <span className="secondary">{c.evidence_type}</span>
                <span>{c.title}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="card">
        <h2>{t("workspace.overviewQuality")}</h2>
        <p className="secondary">
          {t("workspace.qualitySources", { count: ov.data_quality.source_kinds })}
          {ov.data_quality.quality_score ? ` · ${ov.data_quality.quality_score}` : ""}
        </p>
      </section>
    </div>
  );
}
