import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatExperienceStatus, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

/**
 * 研究经验卡 Library（UX Foundation / 任务书 §25）：
 * 单请求消费 /views/experience-cards，桌面表格 Layout。
 */

interface ExperienceRow {
  card_id: string;
  title: string;
  instrument_id: string;
  status: string;
  confidence: number;
  current_version: number;
  validation_count: number;
  source_report_id: string;
  updated_at: string | null;
}

function statusClass(status: string): string {
  if (status === "APPROVED") return "status-ok";
  if (status === "REJECTED") return "status-error";
  return "secondary";
}

export function ExperienceCardsPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["experience-cards-view"],
    queryFn: async (): Promise<ExperienceRow[]> => {
      const resp = await fetch("/api/v1/views/experience-cards");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: ExperienceRow[] };
      return body.results;
    },
  });

  return (
    <main className="page" data-testid="experience-page">
      <h1>{t("nav.experience")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && (
        <div className="empty-state">
          <p>{t("experience.empty")}</p>
          <p className="secondary">{t("experience.emptyHint")}</p>
          <Link to="/reports" className="control-btn">
            {t("experience.emptyAction", { defaultValue: t("nav.reports") })}
          </Link>
        </div>
      )}
      {data && data.length > 0 && (
        <table className="data-table" data-testid="experience-table">
          <thead>
            <tr>
              <th>{t("experience.tableTitle")}</th>
              <th>{t("experience.statusLabel")}</th>
              <th>{t("experience.confidenceLabel")}</th>
              <th>{t("experience.validationsShort")}</th>
              <th>{t("experience.versionLabel")}</th>
              <th>{t("experience.updatedLabel")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.card_id} data-testid="experience-row">
                <td>
                  <Link to={`/experience/${row.card_id}`}>{row.title}</Link>
                </td>
                <td>
                  <span className={statusClass(row.status)}>
                    {formatExperienceStatus(row.status, lang)}
                  </span>
                </td>
                <td className="mono">{Math.round(row.confidence * 100)}%</td>
                <td className="mono">{row.validation_count}</td>
                <td className="mono">v{row.current_version}</td>
                <td className="secondary">{formatWhen(row.updated_at, lang)}</td>
                <td>
                  <Link className="control-btn" to={`/experience/${row.card_id}`}>
                    {t("experience.open")}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
