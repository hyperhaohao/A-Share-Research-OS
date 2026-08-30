import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Badge, Panel } from "../../ui/guanlan";
import type { ExperienceView } from "./experienceView";

/**
 * 用（donor 经验知识库 → ASRO 已批准卡片，方案 §14）：
 * 批准门槛在后端（≥1 验证），这里只列真实已批准卡片。
 */
export function ExperienceKnowledgeBase({ view }: { view: ExperienceView }) {
  const { t } = useTranslation();
  return (
    <Panel title={t("experienceWs.kbTitle")} hint={t("experienceWs.kbHint")}>
      {view.kb.length === 0 ? (
        <p className="secondary" data-testid="experience-kb-empty">
          {t("experienceWs.kbEmpty")}
        </p>
      ) : (
        <ul className="watch-list" data-testid="experience-kb">
          {view.kb.map((k) => (
            <li key={k.card_id} className="result-row">
              <Link to={`/experience/${k.card_id}`} className="result-name">
                {k.title ?? k.card_id}
              </Link>
              {k.verdict === "APPROVED" && <Badge tone="ok">{t("experienceWs.verdictApproved")}</Badge>}
              <span className="secondary mono">{Math.round(k.confidence * 100)}%</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
