import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatExperienceStatus, uiLang } from "../../presentation/enumLabels";
import { CardWorkflowPanel } from "../../components/CardWorkflowPanel";
import { ScreeningLaunchButton } from "../../components/ScreeningLaunchButton";
import { ErrorState } from "../../ui/components";
import { fetchExperienceView } from "./experienceView";
import { ExperienceSourcePane } from "./ExperienceSourcePane";
import { ExperienceRefinePane } from "./ExperienceRefinePane";
import { ExperienceValidationPanel } from "./ExperienceValidationPanel";
import { ExperienceKnowledgeBase } from "./ExperienceKnowledgeBase";

/**
 * 研究经验卡工作台（Guanlan Direct Port G3，方案 §14/§34）：
 * 原 → 炼 → 验 → 用 三栏一体（donor validation.jsx 工作台形态，
 * ASRO ExperienceCard/Validation 后端）。禁止做成 CRUD。
 */
export function ExperienceWorkbench() {
  const params = useParams();
  const cardId = params.cardId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();

  const viewQuery = useQuery({
    queryKey: ["experience-view", cardId],
    enabled: cardId !== "",
    queryFn: () => fetchExperienceView(cardId),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["experience-view", cardId] });
    void queryClient.invalidateQueries({ queryKey: ["experience-card", cardId] });
  };

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

  const lastError = validateM.error || approveM.error || rejectM.error;
  const card = viewQuery.data?.card;

  return (
    <main className="page" data-testid="experience-detail">
      <p>
        <Link to="/experience" className="secondary">← {t("nav.experience")}</Link>
      </p>

      {viewQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
      {viewQuery.isError && (
        <ErrorState message={t("experience.notFound")} retry={() => void viewQuery.refetch()} />
      )}

      {card && (
        <>
          <div className="watch-card-head">
            <h1 className="serif">{card.title}</h1>
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

          {/* 生命周期（§25）：原 → 炼 → 验 → 用 */}
          <div className="lifecycle-bar" data-testid="experience-lifecycle">
            {[
              { key: "raw", label: t("experience.lifecycle.raw"), done: true },
              { key: "refine", label: t("experience.lifecycle.refine"), done: true },
              {
                key: "validate",
                label: t("experience.lifecycle.validate"),
                done: card.validations.length > 0,
              },
              {
                key: "use",
                label: t("experience.lifecycle.use"),
                done: card.status === "APPROVED",
              },
            ].map((step, idx) => (
              <span
                key={step.key}
                className={step.done ? "lifecycle-step done" : "lifecycle-step"}
              >
                {idx > 0 && <span className="lifecycle-arrow">→</span>}
                <span className={step.done ? "status-ok" : "secondary"}>{step.label}</span>
              </span>
            ))}
          </div>

          <div className="ew-grid">
            <ExperienceSourcePane view={viewQuery.data!} />
            <ExperienceRefinePane card={card} />
            <div className="ew-col-right">
              <ExperienceValidationPanel card={card} />
              {viewQuery.data && <ExperienceKnowledgeBase view={viewQuery.data} />}
            </div>
          </div>

          <CardWorkflowPanel cardId={card.card_id} />

          <div className="header-controls" data-testid="experience-actions">
            <ScreeningLaunchButton cardId={card.card_id} />
            <button
              type="button"
              className="gl-button gl-button-primary"
              data-testid="experience-validate"
              disabled={validateM.isPending}
              onClick={act(validateM)}
            >
              {t("experience.validate")}
            </button>
            <button
              type="button"
              className="gl-button"
              data-testid="experience-approve"
              disabled={approveM.isPending}
              onClick={act(approveM)}
            >
              {t("experience.approve")}
            </button>
            <button
              type="button"
              className="gl-button"
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
        </>
      )}
    </main>
  );
}
