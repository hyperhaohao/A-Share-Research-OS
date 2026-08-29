import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { newResearchContext } from "../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";

/**
 * ScreeningRun → [做成策略] → HandoffEnvelope + StrategyService (§46)。
 * 先组装（失败显形）→ 解析筛选 artifact → 记录 screening→strategy 信封 →
 * 进入策略详情页。
 */
export function StrategyLaunchButton({ screeningRunId }: { screeningRunId: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (): Promise<string> => {
      const resp = await fetch("/api/v1/strategies/from-screening", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screening_run_id: screeningRunId }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "network.unreachable");
      }
      const created = (await resp.json()) as { strategy: { version_id: string } };

      const screeningArtifact = await artifactByDomain("ScreeningRun", screeningRunId);
      if (screeningArtifact == null) {
        throw new Error("artifact.not_found");
      }
      const envelope = await recordHandoff({
        source_module: "screening",
        target_module: "strategy",
        action: "create_strategy",
        artifact_ids: [screeningArtifact.artifact_id],
        context: newResearchContext({}),
        message: "screening → create_strategy",
      });
      return handoffPath(`/strategy/${created.strategy.version_id}`, envelope);
    },
    onSuccess: (path: string) => navigate(path),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <span className="prediction-create">
      <button
        type="button"
        className="control-btn"
        data-testid="strategy-launch"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {t("strategy.launch")}
      </button>
      {error && (
        <span className="status-error">
          {error === "strategy.unassemblable"
            ? t("strategy.unassemblable")
            : t(`errors.${error}`, { defaultValue: t("common.error") })}
        </span>
      )}
    </span>
  );
}
