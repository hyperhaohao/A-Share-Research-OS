import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { newResearchContext } from "../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";

/**
 * ExperienceCard → [按此经验筛选] → HandoffEnvelope + ScreeningService
 * (§45)。先创建（失败显形）→ 记录 experience→screening 信封 → 进入运行页。
 */
export function ScreeningLaunchButton({ cardId }: { cardId: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (): Promise<string> => {
      const resp = await fetch("/api/v1/screening-runs/from-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "network.unreachable");
      }
      const created = (await resp.json()) as { run: { run_id: string } };

      const cardArtifact = await artifactByDomain("ExperienceCard", cardId);
      if (cardArtifact == null) {
        throw new Error("artifact.not_found");
      }
      const envelope = await recordHandoff({
        source_module: "experience",
        target_module: "screening",
        action: "run_screening",
        artifact_ids: [cardArtifact.artifact_id],
        context: newResearchContext({}),
        message: "experience → run_screening",
      });
      return handoffPath(`/screening/${created.run.run_id}`, envelope);
    },
    onSuccess: (path: string) => navigate(path),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <span className="prediction-create">
      <button
        type="button"
        className="control-btn"
        data-testid="screening-launch"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {t("screening.launch")}
      </button>
      {error && (
        <span className="status-error">
          {t(`errors.${error}`, { defaultValue: t("common.error") })}
        </span>
      )}
    </span>
  );
}
