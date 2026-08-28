/**
 * Research workspace tabs (整改 R4): thesis / financials / valuation /
 * reports — all real API data, no mocks.
 */

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`http_${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Thesis tab (R4.3) — full field display
// ---------------------------------------------------------------------------

interface Thesis {
  thesis_id: string;
  title: string;
  description: string;
  supporting_claims: string[];
  opposing_claims: string[];
  confidence: number;
  status: string;
  catalysts: string[];
  risks: string[];
  trigger_conditions: string[];
  invalidate_conditions: string[];
  created_at: string;
}

export function ThesisTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["theses", instrumentId],
    queryFn: () =>
      fetchJson<{ count: number; results: Thesis[] }>(
        `/api/v1/theses?instrument_id=${encodeURIComponent(instrumentId)}`,
      ),
    refetchInterval: 15000,
  });

  if (isPending) return <p className="mono">{t("common.loading")}</p>;
  if (isError || !data || data.count === 0)
    return <p className="secondary">{t("workspace.noData")}</p>;

  return (
    <div>
      {data.results.map((thesis) => (
        <div key={thesis.thesis_id} className="card" data-testid="thesis-card">
          <h3>{thesis.title}</h3>
          <p>
            <span className="mono">{thesis.status}</span>
            {" · "}
            <span className="mono">{t("workspace.confidence")}: {thesis.confidence}</span>
            {" · "}
            <span className="secondary">{new Date(thesis.created_at).toLocaleString()}</span>
          </p>
          <p>{thesis.description}</p>
          <FieldList label={t("workspace.supportingClaims")} items={thesis.supporting_claims} />
          <FieldList label={t("workspace.opposingClaims")} items={thesis.opposing_claims} />
          <FieldList label={t("workspace.catalysts")} items={thesis.catalysts} />
          <FieldList label={t("workspace.risks")} items={thesis.risks} />
          <FieldList label={t("workspace.triggers")} items={thesis.trigger_conditions} />
          <FieldList label={t("workspace.invalidate")} items={thesis.invalidate_conditions} />
        </div>
      ))}
    </div>
  );
}

function FieldList({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <span className="control-label">{label}</span>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Financials tab (R4.4) — per-period metrics + SVG trend (real data)
// ---------------------------------------------------------------------------

interface FinancialEvidence {
  evidence_id: string;
  available_time: string;
  metadata: {
    report_date?: string;
    eps?: number | null;
    bvps?: number | null;
    roe_pct?: number | null;
    revenue_yuan?: number | null;
    net_profit_yuan?: number | null;
    gross_margin_pct?: number | null;
    revenue_yoy_pct?: number | null;
  };
}

function MetricRow({ label, value, unit }: { label: string; value: unknown; unit: string }) {
  const { t } = useTranslation();
  if (value === null || value === undefined)
    return (
      <div className="result-row">
        <span>{label}</span>
        <span className="secondary">{t("workspace.noData")}</span>
      </div>
    );
  return (
    <div className="result-row">
      <span>{label}</span>
      <span className="mono">
        {typeof value === "number"
          ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
          : String(value)}
        {unit}
      </span>
    </div>
  );
}

export function FinancialsTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["financials", instrumentId],
    queryFn: () =>
      fetchJson<{ count: number; results: FinancialEvidence[] }>(
        `/api/v1/evidence?instrument_id=${encodeURIComponent(instrumentId)}&evidence_type=financial_report`,
      ),
    refetchInterval: 30000,
  });

  if (isPending) return <p className="mono">{t("common.loading")}</p>;
  if (isError || !data || data.count === 0)
    return <p className="secondary">{t("workspace.noData")}</p>;

  const periods = [...data.results].sort(
    (a, b) => (a.metadata.report_date ?? "").localeCompare(b.metadata.report_date ?? ""),
  );
  const latest = periods[periods.length - 1].metadata;

  return (
    <div>
      <div className="card">
        <h2>{t("workspace.latestPeriod", { period: latest.report_date ?? "—" })}</h2>
        <MetricRow label="EPS" value={latest.eps} unit=" 元" />
        <MetricRow label="BVPS" value={latest.bvps} unit=" 元" />
        <MetricRow label="ROE" value={latest.roe_pct} unit="%" />
        <MetricRow label={t("workspace.revenue")} value={latest.revenue_yuan !== null && latest.revenue_yuan !== undefined ? Math.round(latest.revenue_yuan / 1e8) : null} unit=" 亿" />
        <MetricRow label={t("workspace.netProfit")} value={latest.net_profit_yuan !== null && latest.net_profit_yuan !== undefined ? Math.round(latest.net_profit_yuan / 1e8) : null} unit=" 亿" />
        <MetricRow label={t("workspace.grossMargin")} value={latest.gross_margin_pct} unit="%" />
        <MetricRow label={t("workspace.revenueYoY")} value={latest.revenue_yoy_pct} unit="%" />
      </div>

      {periods.length >= 2 && (
        <div className="card">
          <h2>{t("workspace.trend")}</h2>
          <TrendChart
            points={periods.map((p) => ({
              label: p.metadata.report_date ?? "",
              value: p.metadata.roe_pct ?? null,
            }))}
            title={t("workspace.roeTrend")}
          />
          <TrendChart
            points={periods.map((p) => ({
              label: p.metadata.report_date ?? "",
              value:
                p.metadata.revenue_yuan !== null && p.metadata.revenue_yuan !== undefined
                  ? Math.round(p.metadata.revenue_yuan / 1e8)
                  : null,
            }))}
            title={t("workspace.revenueTrend")}
          />
        </div>
      )}
    </div>
  );
}

/** Minimal SVG line chart over real evidence values (no chart dep needed). */
export function TrendChart({
  points,
  title,
}: {
  points: Array<{ label: string; value: number | null }>;
  title: string;
}) {
  const valid = points.filter((p) => p.value !== null) as Array<{ label: string; value: number }>;
  if (valid.length < 2) return null;
  const w = 560;
  const h = 140;
  const pad = 24;
  const values = valid.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = (w - pad * 2) / (valid.length - 1);
  const coords = valid.map((p, i) => ({
    x: pad + i * step,
    y: h - pad - ((p.value - min) / span) * (h - pad * 2),
    ...p,
  }));
  const path = coords.map((c, i) => `${i ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  return (
    <figure>
      <figcaption className="control-label">{title}</figcaption>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title}>
        <path d={path} fill="none" stroke="var(--color-accent)" strokeWidth="2" />
        {coords.map((c, i) => (
          <g key={i}>
            <circle cx={c.x} cy={c.y} r="3" fill="var(--color-accent)" />
            <text x={c.x} y={h - 6} fontSize="9" textAnchor="middle" fill="var(--color-text-secondary)">
              {c.label.slice(2, 7)}
            </text>
            <text x={c.x} y={c.y - 8} fontSize="9" textAnchor="middle" fill="var(--color-text)" className="mono">
              {c.value}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}

// ---------------------------------------------------------------------------
// Valuation tab (R4.5)
// ---------------------------------------------------------------------------

interface Valuation {
  valuation_id: string;
  method: string;
  computable: boolean;
  value: number | null;
  inputs: Record<string, unknown>;
  detail: Record<string, unknown>;
  missing: Array<{ name: string }>;
  scenario_id: string | null;
  thesis_id: string | null;
}

export function ValuationTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["valuations", instrumentId],
    queryFn: () =>
      fetchJson<{ count: number; results: Valuation[] }>(
        `/api/v1/valuations?instrument_id=${encodeURIComponent(instrumentId)}`,
      ),
    refetchInterval: 30000,
  });

  if (isPending) return <p className="mono">{t("common.loading")}</p>;
  if (isError || !data || data.count === 0)
    return <p className="secondary">{t("workspace.noData")}</p>;

  return (
    <div>
      {data.results.map((v) => (
        <div key={v.valuation_id} className="card" data-testid="valuation-card">
          <h3>
            <span className="mono">{v.method}</span>
            {" · "}
            {v.computable ? (
              <span className="mono">
                {t("workspace.impliedPrice")}: {v.value}
                {v.detail.upside_pct !== undefined && (
                  <> · {t("workspace.upside")}: {v.detail.upside_pct}%</>
                )}
              </span>
            ) : (
              <span className="secondary">{t("workspace.notComputable")}</span>
            )}
            {v.scenario_id && <span className="secondary"> · scenario {v.scenario_id.slice(0, 10)}</span>}
          </h3>
          {v.computable ? (
            <p className="secondary">{Object.keys(v.inputs).join(" · ")}</p>
          ) : (
            <p className="status-error">
              {v.missing.map((m) => m.name).join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reports tab (R4.1) — report list inside the workspace
// ---------------------------------------------------------------------------

export function WorkspaceReportsTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["workspace-reports", instrumentId],
    queryFn: () =>
      fetchJson<{ count: number; results: Array<{ report_id: string; language: string; gate_status: string; published: boolean; created_at: string }> }>(
        `/api/v1/reports?instrument_id=${encodeURIComponent(instrumentId)}`,
      ),
    refetchInterval: 20000,
  });

  if (isPending) return <p className="mono">{t("common.loading")}</p>;
  if (isError || !data || data.count === 0)
    return <p className="secondary">{t("workspace.noData")}</p>;

  return (
    <div>
      {data.results.map((r) => (
        <div key={r.report_id} className="result-row">
          <a href={`/reports/${r.report_id}`} className="mono">
            {r.report_id}
          </a>
          <span className="mono">{r.language}</span>
          <span className="mono secondary">{r.gate_status}</span>
          <span className="secondary">{new Date(r.created_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}
