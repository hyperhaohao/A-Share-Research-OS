import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Panel } from "../../ui/guanlan";
import { formatWhen } from "../../presentation/format";
import { formatSourceTrust, uiLang } from "../../presentation/enumLabels";
import type { ExperienceView } from "./experienceView";

/**
 * 原（donor SourcePane → ASRO 真实来源，方案 §14）：
 * 来源报告 + 主张原文（cite 序号 = 卡引用证据的等价标记）+ 证据摘要。
 * 全部真实内容；证据无摘要显形 —。
 */
export function ExperienceSourcePane({ view }: { view: ExperienceView }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  return (
    <div className="ew-pane">
      <Panel
        title={t("experienceWs.sourceTitle")}
        hint={t("experienceWs.sourceHint", {
          claims: view.source.claims.length,
          evidence: view.source.evidence.length,
        })}
        actions={
          <Link to={`/reports/${view.source.report_id}`} className="gl-button gl-button-ghost">
            {t("experienceWs.openSource")} →
          </Link>
        }
      >
        <ul className="ew-claim-list" data-testid="experience-source-claims">
          {view.source.claims.map((c) => (
            <li key={c.claim_id} className="ew-claim">
              <sup className="ew-cite mono">[{c.cite}]</sup>
              <div className="ew-claim-body">
                <p className="ew-claim-text">{c.statement}</p>
                <p className="secondary mono ew-claim-meta">
                  {t(`experienceWs.factStatus.${c.fact_status}`, { defaultValue: "—" })}
                </p>
              </div>
            </li>
          ))}
          {view.source.claims.length === 0 && (
            <li className="secondary">{t("experienceWs.noClaims")}</li>
          )}
        </ul>
      </Panel>

      <Panel title={t("experienceWs.evidenceTitle")} hint={`${view.source.evidence.length}`}>
        <ul className="ew-evidence-list" data-testid="experience-source-evidence">
          {view.source.evidence.map((e, i) => (
            <li key={e.evidence_id} className="ew-evidence">
              <span className="ew-cite mono">[{i + 1}]</span>
              <div>
                <p className="ew-claim-text">{e.summary}</p>
                <p className="secondary mono ew-claim-meta">
                  <span className="gl-badge" data-testid="evidence-trust">
                    {formatSourceTrust(e.authority_level, lang)}
                  </span>
                  {" · "}
                  {e.source} · {formatWhen(e.available_time, lang)}
                </p>
              </div>
            </li>
          ))}
          {view.source.evidence.length === 0 && (
            <li className="secondary">{t("experienceWs.noEvidence")}</li>
          )}
        </ul>
      </Panel>
    </div>
  );
}
