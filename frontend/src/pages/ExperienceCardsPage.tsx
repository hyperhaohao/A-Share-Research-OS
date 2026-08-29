import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatExperienceStatus, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

export interface CardSummary {
  card_id: string;
  title: string;
  status: string;
  statement: string;
  current_version: number;
  created_at: string | null;
}

export function statusClass(status: string): string {
  if (status === "APPROVED") return "status-ok";
  if (status === "REJECTED") return "status-error";
  return "secondary";
}

/** 经验卡列表页（Phase C v1）。 */
export function ExperienceCardsPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["experience-cards"],
    queryFn: async (): Promise<CardSummary[]> => {
      const resp = await fetch("/api/v1/experience-cards");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: CardSummary[] };
      return body.results;
    },
  });

  return (
    <main className="page" data-testid="experience-page">
      <h1>{t("nav.experience")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("experience.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list watch-cards">
          {data.map((card) => (
            <li className="card watch-card" key={card.card_id} data-testid="experience-card">
              <div className="watch-card-head">
                <Link to={`/experience/${card.card_id}`} className="watch-card-name">
                  {card.title}
                </Link>
                <span className={statusClass(card.status)}>
                  {formatExperienceStatus(card.status, lang)}
                </span>
              </div>
              <div className="task-grid">
                <span>{t("experience.statementLabel")}</span>
                <span>{card.statement}</span>
                <span>{t("experience.versionLabel")}</span>
                <span className="mono">v{card.current_version}</span>
                <span>{t("experience.createdLabel")}</span>
                <span>{formatWhen(card.created_at, lang)}</span>
              </div>
              <div className="header-controls">
                <Link className="control-btn" to={`/experience/${card.card_id}`}>
                  {t("experience.open")}
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
