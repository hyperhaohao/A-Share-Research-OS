import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Badge, Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen as formatWhenTime } from "../../presentation/format";
import type { ExperienceCardDetail } from "./experienceView";

/**
 * 验（donor 验证区 → ASRO 真实验证，方案 §14/§34）：
 * 裁决 chip（通过/存疑/驳回/未验证）+ 验证记录 + 量化指标区
 * （无量化验证 → 诚实留空，不编 IC/ICIR —— donor synthVal 教训已成红线）。
 */

function verdictChip(
  card: ExperienceCardDetail,
  t: (k: string) => string,
): { tone: "ok" | "error" | "warning" | "neutral"; label: string } {
  if (card.status === "APPROVED") return { tone: "ok", label: t("experienceWs.verdictApproved") };
  if (card.status === "REJECTED") return { tone: "error", label: t("experienceWs.verdictRejected") };
  if (card.validations.length > 0 || card.status === "VALIDATING")
    return { tone: "warning", label: t("experienceWs.verdictDoubtful") };
  return { tone: "neutral", label: t("experienceWs.verdictPending") };
}

export function ExperienceValidationPanel({ card }: { card: ExperienceCardDetail }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const chip = verdictChip(card, t);
  return (
    <div className="ew-pane">
      <Panel
        title={t("experienceWs.validateTitle")}
        actions={<Badge tone={chip.tone === "neutral" ? "neutral" : chip.tone}>{chip.label}</Badge>}
      >
        <div className="ew-metrics" data-testid="experience-metrics">
          <div className="cc-brief-cell">
            <div className="cc-brief-label">IC</div>
            <div className="num">—</div>
          </div>
          <div className="cc-brief-cell">
            <div className="cc-brief-label">ICIR</div>
            <div className="num">—</div>
          </div>
          <div className="cc-brief-cell">
            <div className="cc-brief-label">{t("experienceWs.confidence")}</div>
            <div className="num">{Math.round(card.confidence * 100)}%</div>
          </div>
        </div>
        <p className="secondary ew-metrics-hint">{t("experienceWs.metricsPending")}</p>

        <ul className="watch-list" data-testid="experience-validations">
          {card.validations.map((v) => (
            <li className="result-row" key={v.validation_id}>
              <span className="secondary mono">{formatWhenTime(v.created_at, lang)}</span>
              <span className="ew-validation-summary">{v.summary}</span>
            </li>
          ))}
          {card.validations.length === 0 && (
            <li className="secondary">{t("experience.noValidations")}</li>
          )}
        </ul>

        <div className="ew-workflow-cta">
          <Link to="/workflow-studio" className="gl-button">
            {t("workflows.studioTitle")} →
          </Link>
        </div>
      </Panel>
    </div>
  );
}
