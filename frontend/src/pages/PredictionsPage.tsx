import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatDirection, formatHorizon, uiLang } from "../presentation/enumLabels";
import { formatPct, formatWhen } from "../presentation/format";
import { useInstrumentName } from "../shared/instrument";

interface PredictionItem {
  prediction_id: string;
  instrument_id: string;
  horizon: string;
  expected_direction: string;
  expected_return_range: [number, number];
  consistency?: "consistent" | "conflict";
  consistency_note?: string;
  due_at: string;
  supporting_thesis_id: string | null;
  validation?: {
    instrument_return_pct: number;
    direction_correct: boolean | null;
    range_hit: boolean;
  };
}

/** List-all predictions (PW2 §16: no seed hardcode, no N+1 per instrument). */
/** UX Foundation: 单请求消费 /views/prediction-review（KPI + 冲突 + 名称装配）。 */
interface PredictionReviewView {
  results: Array<
    PredictionItem & {
      instrument?: { instrument_id: string; name: string | null; code: string } | null;
    }
  >;
  kpi: {
    total: number;
    validated: number;
    direction_accuracy: number | null;
    range_hit_rate: number | null;
    avg_return_pct: number | null;
    conflicts: number;
  };
  generated_at: string | null;
}

async function fetchPredictionReview(): Promise<PredictionReviewView> {
  const resp = await fetch("/api/v1/views/prediction-review");
  if (!resp.ok) throw new Error("network.unreachable");
  return resp.json();
}

function PredictionCard({
  prediction: p,
  instrument,
}: {
  prediction: PredictionItem;
  instrument?: { instrument_id: string; name: string | null; code: string } | null;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const nameFallback = useInstrumentName(p.instrument_id);
  const [lo, hi] = p.expected_return_range;

  return (
    <li className="card watch-card" data-testid="prediction-card">
      <div className="watch-card-head">
        <Link to={`/instrument/${p.instrument_id}`} className="watch-card-name">
          {instrument?.name ?? nameFallback?.name ?? p.instrument_id}
          {instrument?.code ? ` · ${instrument.code}` : ""}
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
        {p.consistency === "conflict" && (
          <span className="status-error" data-testid="prediction-conflict">
            ⚠ {p.consistency_note}
          </span>
        )}
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
  const viewQuery = useQuery({
    queryKey: ["prediction-review-view"],
    queryFn: fetchPredictionReview,
  });
  const view = viewQuery.data;
  const kpi = view?.kpi;
  const perf = kpi
    ? {
        total_validations: kpi.validated,
        direction_accuracy: kpi.direction_accuracy,
        average_excess_return_pct: kpi.avg_return_pct,
        range_hit_rate: kpi.range_hit_rate,
      }
    : undefined;
  const predictions = view?.results ?? [];

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
        {predictions.length === 0 && (
          <p className="secondary">{t("predictions.emptyHint")}</p>
        )}
        <ul className="watch-list watch-cards">
          {predictions.map((p) => (
            <PredictionCard key={p.prediction_id} prediction={p} instrument={p.instrument} />
          ))}
        </ul>
      </section>
    </main>
  );
}
