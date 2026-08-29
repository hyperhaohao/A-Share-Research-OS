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

const TABS = [
  "overview",
  "timeline",
  "graph",
  "thesis",
  "financials",
  "valuation",
  "evidence",
  "reports",
  "predictions",
] as const;
type WorkspaceTab = (typeof TABS)[number];

/** Stock Workspace (任务书 §58): header + Overview/Timeline/Graph/Evidence/Predictions. */
export function InstrumentWorkspacePage() {
  const { instrumentId = "" } = useParams();
  const { t } = useTranslation();
  const [tab, setTab] = useState<WorkspaceTab>("overview");

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
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? "control-btn active" : "control-btn"}
            onClick={() => setTab(key)}
          >
            {t(`workspace.tab.${key}`)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
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

      {tab === "timeline" && <TimelineTab instrumentId={instrumentId} />}
      {tab === "graph" && <FlowGraphTab instrumentId={instrumentId} />}
      {tab === "thesis" && <ThesisTab instrumentId={instrumentId} />}
      {tab === "financials" && <FinancialsTab instrumentId={instrumentId} />}
      {tab === "valuation" && <ValuationTab instrumentId={instrumentId} />}
      {tab === "reports" && <WorkspaceReportsTab instrumentId={instrumentId} />}

      {tab === "evidence" && (
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

      {tab === "predictions" && (
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
