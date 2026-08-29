import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";
import { useInstrumentName } from "../shared/instrument";

interface Candidate {
  instrument_id: string;
  code: string;
  name: string;
  rank: number;
  score: number;
  matched_rules: string[];
  explanation: string;
  risks: string[];
  experience_card_refs: string[];
}

interface ScreeningRun {
  run_id: string;
  card_id: string | null;
  universe_size: number;
  rules: Array<Record<string, unknown>>;
  candidates: Candidate[];
  excluded_summary: Record<string, unknown>;
  status: string;
  error: string | null;
  created_at: string | null;
}

export function ScreeningRunsPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["screening-runs"],
    queryFn: async (): Promise<ScreeningRun[]> => {
      const resp = await fetch("/api/v1/screening-runs?limit=20");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: ScreeningRun[] };
      return body.results;
    },
  });

  return (
    <main className="page" data-testid="screening-page">
      <h1>{t("nav.screening")}</h1>
      <p className="secondary">{t("screening.pageHint")}</p>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("screening.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((run) => (
            <li className="result-row" key={run.run_id} data-testid="screening-run-row">
              <Link to={`/screening/${run.run_id}`} className="result-name">
                {t("screening.runTitle", { rank: run.candidates.length, universe: run.universe_size })}
              </Link>
              <span className={run.status === "failed" ? "status-error" : run.status === "completed" ? "status-ok" : "secondary"}>
                {t(`workflow.status.${run.status}`)}
              </span>
              <span className="secondary">{formatWhen(run.created_at, lang)}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function CandidateRow({ candidate }: { candidate: Candidate }) {
  const profile = useInstrumentName(candidate.instrument_id);
  const name = profile?.name ?? candidate.name;
  return (
    <li className="card watch-card" data-testid="screening-candidate">
      <div className="watch-card-head">
        <Link to={`/instrument/${candidate.instrument_id}`} className="watch-card-name">
          #{candidate.rank} · {name} · {candidate.code}
        </Link>
        <span className="mono">{candidate.score}</span>
      </div>
      <p data-testid="candidate-explanation">{candidate.explanation}</p>
      {candidate.risks.length > 0 && (
        <ul className="watch-list">
          {candidate.risks.map((r) => (
            <li key={r} className="secondary">⚠ {r}</li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function ScreeningRunDetailPage() {
  const params = useParams();
  const runId = params.runId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["screening-run", runId],
    enabled: runId !== "",
    refetchInterval: 2000,
    queryFn: async (): Promise<ScreeningRun> => {
      const resp = await fetch(`/api/v1/screening-runs/${runId}`);
      if (!resp.ok) throw new Error("screening.not_found");
      const body = (await resp.json()) as { run: ScreeningRun };
      return body.run;
    },
  });

  if (isPending) {
    return (
      <main className="page" data-testid="screening-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError || !data) {
    return (
      <main className="page" data-testid="screening-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  const excluded = data.excluded_summary as {
    universe_size?: number;
    candidate_count?: number;
    excluded_by_rule?: Record<string, number>;
    examples?: Record<string, string>;
  };

  return (
    <main className="page" data-testid="screening-detail">
      <p>
        <Link to="/screening" className="secondary">← {t("nav.screening")}</Link>
      </p>
      <h1>{t("screening.detailTitle")}</h1>
      <p className="secondary">
        {t("screening.universeSize", { universe: data.universe_size })} ·{" "}
        {t("screening.candidateCount", { count: data.candidates.length })} ·{" "}
        {formatWhen(data.created_at, lang)}
      </p>

      {data.status === "running" && <p className="secondary">{t("workflow.running")}</p>}
      {data.status === "failed" && (
        <p className="status-error">{t("workflow.failed")}: {data.error}</p>
      )}

      {data.status === "completed" && (
        <>
          <section className="card" data-testid="screening-excluded">
            <h2>{t("screening.excludedTitle")}</h2>
            <div className="task-grid">
              {Object.entries(excluded?.excluded_by_rule ?? {}).map(([kind, count]) => (
                <span key={kind} className="secondary">
                  {t(`screening.rule.${kind}`)}: {count}
                  {excluded?.examples?.[kind] ? `（例：${excluded.examples[kind]}）` : ""}
                </span>
              ))}
            </div>
          </section>

          <ul className="watch-list watch-cards">
            {data.candidates.map((c) => (
              <CandidateRow key={c.instrument_id} candidate={c} />
            ))}
          </ul>
          {data.candidates.length === 0 && (
            <p className="secondary">{t("screening.noCandidates")}</p>
          )}
        </>
      )}
    </main>
  );
}
