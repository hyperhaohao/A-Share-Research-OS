import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatExperienceStatus, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";
import { CardWorkflowPanel } from "../components/CardWorkflowPanel";
import { ScreeningLaunchButton } from "../components/ScreeningLaunchButton";

interface ValidationItem {
  validation_id: string;
  method: string;
  summary: string;
  created_at: string | null;
}

interface CardDetail {
  card_id: string;
  instrument_id: string;
  title: string | null;
  status: string;
  statement: string;
  mechanism: string;
  applicable_conditions: string[];
  invalid_conditions: string[];
  source_report_id: string;
  source_claim_ids: string[];
  source_evidence_ids: string[];
  current_version: number;
  refine_method: string;
  confidence: number;
  verdict: string | null;
  versions: Array<{
    version_no: number;
    method: string;
    created_at: string | null;
  }>;
  validations: ValidationItem[];
  created_at: string | null;
}

function useCardQuery(cardId: string) {
  return useQuery({
    queryKey: ["experience-card", cardId],
    enabled: cardId !== "",
    queryFn: async (): Promise<CardDetail> => {
      const resp = await fetch(`/api/v1/experience-cards/${cardId}`);
      if (!resp.ok) throw new Error("experience.not_found");
      const body = (await resp.json()) as { card: CardDetail };
      return body.card;
    },
  });
}

/** 经验卡详情（Phase C v1）：原→炼→验→用的产品面（§13/§43）。 */
export function ExperienceCardPage() {
  const params = useParams();
  const cardId = params.cardId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();
  const cardQuery = useCardQuery(cardId);
  const card = cardQuery.data;

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["experience-card", cardId] });

  const post = async (path: string, body?: Record<string, unknown>) => {
    const resp = await fetch(`/api/v1/experience-cards/${cardId}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) {
      const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
      throw new Error(err?.error_code ?? "network.unreachable");
    }
    await resp.json();
    invalidate();
  };

  const validateM = useMutation({ mutationFn: () => post("validate") });
  const approveM = useMutation({ mutationFn: () => post("approve", { verdict: null }) });
  const rejectM = useMutation({ mutationFn: () => post("reject", { verdict: null }) });

  const act = (m: { mutate: () => void }) => () => m.mutate();

  if (cardQuery.isPending) {
    return (
      <main className="page" data-testid="experience-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (cardQuery.isError || !card) {
    return (
      <main className="page" data-testid="experience-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  const lastError = validateM.error || approveM.error || rejectM.error;

  return (
    <main className="page" data-testid="experience-detail">
      <p>
        <Link to="/experience" className="secondary">← {t("nav.experience")}</Link>
      </p>
      <div className="watch-card-head">
        <h1>{card.title}</h1>
        <span
          className={
            card.status === "APPROVED"
              ? "status-ok"
              : card.status === "REJECTED"
                ? "status-error"
                : "secondary"
          }
        >
          {formatExperienceStatus(card.status, lang)}
        </span>
      </div>
      <p className="secondary">
        {t("experience.confidenceLabel")}: {Math.round(card.confidence * 100)}% · v
        {card.current_version} · {t(`experience.method.${card.refine_method}`)}
      </p>

      <section className="card">
        <h2>{t("experience.statementLabel")}</h2>
        <p>{card.statement}</p>
        <h2>{t("experience.mechanismLabel")}</h2>
        <p>{card.mechanism}</p>
      </section>

      <section className="card">
        <h2>{t("experience.conditionsTitle")}</h2>
        <div className="task-grid">
          <span>{t("experience.applicableLabel")}</span>
          <span>{card.applicable_conditions.length ? card.applicable_conditions.join("；") : "—"}</span>
          <span>{t("experience.invalidLabel")}</span>
          <span>{card.invalid_conditions.length ? card.invalid_conditions.join("；") : "—"}</span>
        </div>
      </section>

      <section className="card">
        <h2>{t("experience.sourcesTitle")}</h2>
        <div className="task-grid">
          <span>{t("experience.sourceReport")}</span>
          <span>
            <Link to={`/reports/${card.source_report_id}`}>{t("experience.openSourceReport")}</Link>
          </span>
          <span>{t("experience.claimsCount")}</span>
          <span>{card.source_claim_ids.length}</span>
          <span>{t("experience.evidenceCount")}</span>
          <span>{card.source_evidence_ids.length}</span>
        </div>
      </section>

      <CardWorkflowPanel cardId={card.card_id} />

      <section className="card">
        <h2>{t("experience.validationsTitle")}</h2>
        {card.validations.length === 0 && (
          <p className="secondary">{t("experience.noValidations")}</p>
        )}
        <ul className="watch-list">
          {card.validations.map((v) => (
            <li className="result-row" key={v.validation_id}>
              <span className="secondary">{formatWhen(v.created_at, lang)}</span>
              <span>{v.summary}</span>
            </li>
          ))}
        </ul>
      </section>

      <div className="header-controls" data-testid="experience-actions">
        <ScreeningLaunchButton cardId={card.card_id} />
        <button
          type="button"
          className="control-btn"
          data-testid="experience-validate"
          disabled={validateM.isPending}
          onClick={act(validateM)}
        >
          {t("experience.validate")}
        </button>
        <button
          type="button"
          className="control-btn"
          data-testid="experience-approve"
          disabled={approveM.isPending}
          onClick={act(approveM)}
        >
          {t("experience.approve")}
        </button>
        <button
          type="button"
          className="control-btn"
          data-testid="experience-reject"
          disabled={rejectM.isPending}
          onClick={act(rejectM)}
        >
          {t("experience.reject")}
        </button>
        {lastError instanceof Error && (
          <span className="status-error">
            {t(`errors.${lastError.message}`, { defaultValue: t("common.error") })}
          </span>
        )}
      </div>
    </main>
  );
}
