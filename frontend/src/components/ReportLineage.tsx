import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { formatArtifactType, formatRelation, uiLang } from "../presentation/enumLabels";
import {
  artifactByDomain,
  type Artifact,
} from "../shared/handoff";

interface LineageNode {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
  relation: string;
  depth: number;
}

interface Lineage {
  artifact: Artifact | null;
  upstream: LineageNode[];
  downstream: LineageNode[];
}

async function fetchLineage(artifactId: string): Promise<Lineage | null> {
  const resp = await fetch(`/api/v1/artifacts/${encodeURIComponent(artifactId)}/lineage`);
  if (!resp.ok) return null;
  return resp.json();
}

/**
 * 报告 → 研究脉络（V2 Phase A, E2E-07 的产品面）：展开后沿 Artifact
 * Registry 回溯上游（报告版本 ← 研究运行）与下游（预测/验证）。
 * 每行都是业务名 + 溯源关系，技术 id 收在链接里。
 */
export function ReportLineage({ reportId }: { reportId: string }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [open, setOpen] = useState(false);

  const artifactQuery = useQuery({
    queryKey: ["report-artifact", reportId],
    enabled: open,
    staleTime: 30000,
    queryFn: () => artifactByDomain("Report", reportId),
  });
  const lineageQuery = useQuery({
    queryKey: ["report-lineage", artifactQuery.data?.artifact_id],
    enabled: open && artifactQuery.data != null,
    staleTime: 30000,
    queryFn: () => fetchLineage(artifactQuery.data!.artifact_id),
  });

  const lineage = lineageQuery.data ?? null;

  const row = (node: LineageNode) => (
    <li className="result-row" key={node.artifact_id}>
      <span className="secondary">{formatRelation(node.relation, lang)}</span>
      <Link to={node.route || "#"} className="result-name">
        {formatArtifactType(node.artifact_type, lang)} · {node.title}
      </Link>
      <span className="secondary">{t("lineage.depth", { count: node.depth })}</span>
    </li>
  );

  return (
    <div className="report-lineage" data-testid="report-lineage">
      <button type="button" className="control-btn" onClick={() => setOpen((v) => !v)}>
        {open ? t("lineage.hide") : t("lineage.show")}
      </button>
      {open && (
        <div className="lineage-body">
          {artifactQuery.data == null && (
            <p className="secondary">{t("lineage.noArtifact")}</p>
          )}
          {artifactQuery.data != null && lineage == null && (
            <p className="secondary">{t("common.loading")}</p>
          )}
          {lineage != null && (
            <>
              <p className="secondary">{t("lineage.upstreamTitle")}</p>
              <ul className="result-list">
                {lineage.upstream.length === 0 ? (
                  <li className="secondary">{t("lineage.empty")}</li>
                ) : (
                  lineage.upstream.map(row)
                )}
              </ul>
              <p className="secondary">{t("lineage.downstreamTitle")}</p>
              <ul className="result-list">
                {lineage.downstream.length === 0 ? (
                  <li className="secondary">{t("lineage.empty")}</li>
                ) : (
                  lineage.downstream.map(row)
                )}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
