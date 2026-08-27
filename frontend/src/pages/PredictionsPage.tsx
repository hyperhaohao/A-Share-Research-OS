import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

interface Performance {
  total_validations: number;
  direction_accuracy: number | null;
  average_excess_return_pct: number | null;
  range_hit_rate: number | null;
}

interface PredictionItem {
  prediction_id: string;
  instrument_id: string;
  horizon: string;
  expected_direction: string;
  expected_return_range: [number, number];
  due_at: string;
  validation?: {
    instrument_return_pct: number;
    direction_correct: boolean | null;
    range_hit: boolean;
  };
}

async function fetchPerformance(): Promise<Performance> {
  const resp = await fetch("/api/v1/regression/performance");
  if (!resp.ok) throw new Error("network.unreachable");
  return resp.json();
}

async function fetchAllPredictions(): Promise<PredictionItem[]> {
  // aggregate across instruments currently in the watchlist + SSE:600519 seed
  const watch = await fetch("/api/v1/watchlist").then((r) => r.json());
  const ids: string[] = (watch.results ?? []).map((w: { instrument_id: string }) => w.instrument_id);
  if (!ids.includes("SSE:600519")) ids.push("SSE:600519");
  const results: PredictionItem[] = [];
  for (const id of ids) {
    const resp = await fetch(`/api/v1/predictions?instrument_id=${encodeURIComponent(id)}`);
    if (!resp.ok) continue;
    const body = await resp.json();
    results.push(...body.results);
  }
  return results;
}

export function PredictionsPage() {
  const { t } = useTranslation();
  const perfQuery = useQuery({ queryKey: ["performance"], queryFn: fetchPerformance });
  const predsQuery = useQuery({ queryKey: ["predictions-all"], queryFn: fetchAllPredictions });

  const perf = perfQuery.data;

  return (
    <main className="page" data-testid="predictions-page">
      <h1>{t("nav.predictions")}</h1>

      <section className="card">
        <h2>{t("predictions.performance")}</h2>
        <ul className="watch-list">
          <li className="result-row">
            <span>{t("predictions.total")}</span>
            <span className="mono">{perf?.total_validations ?? "—"}</span>
          </li>
          <li className="result-row">
            <span>{t("predictions.directionAccuracy")}</span>
            <span className="mono">
              {perf?.direction_accuracy != null ? `${perf.direction_accuracy}%` : "—"}
            </span>
          </li>
          <li className="result-row">
            <span>{t("predictions.avgExcess")}</span>
            <span className="mono">
              {perf?.average_excess_return_pct != null
                ? `${perf.average_excess_return_pct}%`
                : "—"}
            </span>
          </li>
          <li className="result-row">
            <span>{t("predictions.rangeHit")}</span>
            <span className="mono">
              {perf?.range_hit_rate != null ? `${perf.range_hit_rate}%` : "—"}
            </span>
          </li>
        </ul>
      </section>

      <section className="card">
        <h2>{t("workspace.predictions")}</h2>
        {predsQuery.data?.length === 0 && <p className="secondary">{t("label.no_data")}</p>}
        <ul className="watch-list">
          {(predsQuery.data ?? []).map((p) => (
            <li key={p.prediction_id} className="result-row">
              <span className="mono">{p.instrument_id}</span>
              <span className="mono">{p.horizon}</span>
              <span>{t(`workspace.direction.${p.expected_direction}`)}</span>
              {p.validation ? (
                <span className={p.validation.direction_correct ? "status-ok mono" : "status-error mono"}>
                  {p.validation.instrument_return_pct}%
                </span>
              ) : (
                <span className="secondary">{t("predictions.pending")}</span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
