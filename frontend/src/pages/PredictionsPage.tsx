import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatDirection, formatHorizon, uiLang } from "../presentation/enumLabels";
import { formatPct, formatWhen } from "../presentation/format";

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
  supporting_thesis_id: string | null;
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

/** List-all predictions (PW2 §16: no seed hardcode, no N+1 per instrument). */
async function fetchAllPredictions(): Promise<PredictionItem[]> {
  const resp = await fetch("/api/v1/predictions");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
}

function useInstrumentName(instrumentId: string) {
  const { data } = useQuery({
    queryKey: ["instrument", instrumentId],
    staleTime: 60000,
    queryFn: async (): Promise<{ name: string; code: string } | null> => {
      const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(instrumentId)}`);
      if (!resp.ok) return null;
      const body = await resp.json();
      return body.instrument;
    },
  });
  return data;
}

function PredictionCard({ prediction: p }: { prediction: PredictionItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const name = useInstrumentName(p.instrument_id);
  const [lo, hi] = p.expected_return_range;

  return (
    <li className="card watch-card" data-testid="prediction-card">
      <div className="watch-card-head">
        <Link to={`/instrument/${p.instrument_id}`} className="watch-card-name">
          {name?.name ?? p.instrument_id}
          {name ? ` · ${name.code}` : ""}
        </Link>
        <span className="secondary">{formatHorizon(p.horizon, lang)}</span>
      </div>
      <div className="task-grid">
        <span>{t("predictions.directionLabel")}</span>
        <span>{formatDirection(p.expected_direction, lang)}</span>
        <span>{t("predictions.rangeLabel")}</span>
        <span className="mono">
          {formatPct(lo)} ~ {formatPct(hi)}
        </span>
        <span>{t("predictions.statusLabel")}</span>
        {p.validation ? (
          <span className={p.validation.direction_correct ? "status-ok" : "status-error"}>
            {t("predictions.validated")}: {formatPct(p.validation.instrument_return_pct)}
            {p.validation.direction_correct != null
              ? ` · ${p.validation.direction_correct ? t("predictions.directionOk") : t("predictions.directionMiss")}`
              : ""}
          </span>
        ) : (
          <span className="secondary">
            {t("predictions.pending")} · {formatWhen(p.due_at, lang)}
          </span>
        )}
      </div>
      <div className="header-controls">
        <Link className="control-btn" to={`/instrument/${p.instrument_id}`}>
          {t("predictions.viewBasis")}
        </Link>
      </div>
    </li>
  );
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
        {predsQuery.data?.length === 0 && (
          <p className="secondary">{t("predictions.emptyHint")}</p>
        )}
        <ul className="watch-list watch-cards">
          {(predsQuery.data ?? []).map((p) => (
            <PredictionCard key={p.prediction_id} prediction={p} />
          ))}
        </ul>
      </section>
    </main>
  );
}
