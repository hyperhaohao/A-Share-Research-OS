import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { type Plan } from "./CommandPlanSteps";
import { formatArtifactType, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";
import { useInstrumentName } from "../shared/instrument";

interface ArtifactLike {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
}

interface RecentArtifact extends ArtifactLike {
  instrument_ids: string[];
  created_at: string | null;
}

function ArtifactRow({ artifact }: { artifact: ArtifactLike }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const isReport = artifact.artifact_type === "report";
  return (
    <li className="result-row" data-testid="artifact-row">
      <Link to={artifact.route || "#"} className="result-name">
        {artifact.title}
      </Link>
      <span className="secondary">{formatArtifactType(artifact.artifact_type, lang)}</span>
      {isReport && (
        <Link to={artifact.route || "#"} className="control-btn" data-testid="artifact-open">
          {t("commander.openReport")}
        </Link>
      )}
    </li>
  );
}

/**
 * 右栏（总纲 §38）：当前研究产物。优先渲染当前计划产出的 Artifact
 * （报告/预测）；没有活跃计划时显示最近产物。产物永远链接到业务页面。
 */
export function ArtifactsPanel({ activePlan }: { activePlan: Plan | null }) {
  const { t } = useTranslation();

  const planArtifactIds = (activePlan?.steps ?? [])
    .flatMap((s) => s.artifact_ids)
    .filter((id) => id.startsWith("art_"));

  const planArtifacts = useQuery({
    queryKey: ["plan-artifacts", planArtifactIds.join(",")],
    enabled: planArtifactIds.length > 0,
    staleTime: 10000,
    queryFn: async (): Promise<ArtifactLike[]> => {
      const results = await Promise.all(
        planArtifactIds.map(async (id) => {
          const resp = await fetch(`/api/v1/artifacts/${id}`);
          if (!resp.ok) return null;
          const body = (await resp.json()) as { artifact: ArtifactLike };
          return body.artifact;
        }),
      );
      return results.filter((a): a is ArtifactLike => a != null);
    },
  });

  const recent = useQuery({
    queryKey: ["recent-artifacts"],
    enabled: planArtifactIds.length === 0,
    refetchInterval: 15000,
    queryFn: async (): Promise<RecentArtifact[]> => {
      const resp = await fetch("/api/v1/artifacts?limit=8");
      if (!resp.ok) return [];
      const body = (await resp.json()) as { results: RecentArtifact[] };
      return body.results;
    },
  });

  const artifacts: ArtifactLike[] =
    planArtifactIds.length > 0 ? (planArtifacts.data ?? []) : (recent.data ?? []);

  return (
    <section className="card artifacts-panel" data-testid="commander-artifacts">
      <h2>{t("commander.artifacts")}</h2>
      {artifacts.length === 0 ? (
        <p className="secondary">{t("commander.noArtifacts")}</p>
      ) : (
        <ul className="watch-list">
          {artifacts.map((a) => (
            <ArtifactRow key={a.artifact_id} artifact={a} />
          ))}
        </ul>
      )}
      <p className="secondary artifacts-hint">{t("commander.artifactsHint")}</p>
    </section>
  );
}

/** 左栏「最近研究」行（计划 + 运行）。 */
export function PlanRow({ plan }: { plan: Plan }) {
  const { i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(plan.instrument_id);
  return (
    <li className="result-row" data-testid="plan-row">
      <span className="result-name">{plan.title}{profile ? ` · ${profile.name}` : ""}</span>
      <span className={plan.status === "failed" ? "status-error" : plan.status === "completed" ? "status-ok" : "secondary"}>
        {i18n.t(`commander.status.${plan.status}`)}
      </span>
      <span className="secondary">{formatWhen(plan.updated_at, lang)}</span>
    </li>
  );
}
