import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { newResearchContext } from "../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";

/**
 * Report → [炼成经验卡] → HandoffEnvelope + ExperienceService (§43/§72).
 * 先创建（失败显形、不留死信封）→ 解析报告 artifact → 记录
 * report→experience 信封 → 搁溯源参数进入卡片页。
 */
export function ExperienceCardCreateButton({
  reportId,
  instrumentId,
}: {
  reportId: string;
  instrumentId?: string | null;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (): Promise<string> => {
      const resp = await fetch("/api/v1/experience-cards/from-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "network.unreachable");
      }
      const created = (await resp.json()) as {
        card: { card_id: string; instrument_id: string };
      };

      const reportArtifact = await artifactByDomain("Report", reportId);
      if (reportArtifact == null) {
        throw new Error("artifact.not_found");
      }
      const envelope = await recordHandoff({
        source_module: "report",
        target_module: "experience",
        action: "create_experience_draft",
        artifact_ids: [reportArtifact.artifact_id],
        context: newResearchContext({
          primary_instrument_id: instrumentId ?? created.card.instrument_id,
          instrument_ids: [created.card.instrument_id],
        }),
        message: "report → create_experience_draft",
      });
      return handoffPath(`/experience/${created.card.card_id}`, envelope);
    },
    onSuccess: (path: string) => {
      queryClient.invalidateQueries({ queryKey: ["experience-cards"] });
      navigate(path);
    },
    onError: (err: Error) => setError(err.message),
  });

  if (error) {
    return (
      <span className="prediction-create" data-testid="experience-create">
        <button
          type="button"
          className="control-btn"
          disabled={mutation.isPending}
          onClick={() => {
            setError(null);
            mutation.mutate();
          }}
        >
          {t("experience.create")}
        </button>
        <span className="status-error">
          {error === "experience.underivable"
            ? t("experience.underivable")
            : t(`errors.${error}`, { defaultValue: t("common.error") })}
        </span>
      </span>
    );
  }
  return (
    <button
      type="button"
      className="control-btn"
      data-testid="experience-create"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {t("experience.create")}
    </button>
  );
}
