import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

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

export { ScreeningWorkbench as ScreeningRunDetailPage } from "../features/screening-workbench/ScreeningWorkbench";
