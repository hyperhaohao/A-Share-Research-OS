import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { newResearchContext } from "../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";

/**
 * Report → [生成预测] → HandoffEnvelope + PredictionBuilder
 * (V2 Phase A: 跨模块动作走信封, HANDOFF-PROTOCOL §2; PW2 §17).
 *
 * 顺序：先创建（失败显形、无信封不留死信封）→ 解析报告 artifact →
 * 记录 report→prediction:create_prediction 信封 → 携 handoff/context 跳转。
 * Refusals (422 prediction.underivable) surface the honest reason.
 */
export function PredictionCreateButton({
  reportId,
  instrumentId,
}: {
  reportId: string;
  instrumentId?: string | null;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [horizon, setHorizon] = useState("5D");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const resp = await fetch("/api/v1/predictions/from-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_id: reportId, horizon }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "network.unreachable");
      }
      const created = (await resp.json()) as { prediction: { instrument_id: string } };

      // the prediction now exists → its source report artifact is registered
      // (pipeline on fresh reports, from-report fallback on legacy ones)
      const reportArtifact = await artifactByDomain("Report", reportId);
      if (reportArtifact == null) {
        throw new Error("artifact.not_found");
      }
      const envelope = await recordHandoff({
        source_module: "report",
        target_module: "prediction",
        action: "create_prediction",
        artifact_ids: [reportArtifact.artifact_id],
        context: newResearchContext({
          primary_instrument_id: instrumentId ?? created.prediction.instrument_id,
          instrument_ids: [created.prediction.instrument_id],
        }),
        message: "report → create_prediction",
      });
      return handoffPath("/predictions", envelope);
    },
    onSuccess: (path) => navigate(path),
    onError: (err: Error) => setError(err.message),
  });

  if (!open) {
    return (
      <button type="button" className="control-btn" onClick={() => setOpen(true)}>
        {t("predictions.create")}
      </button>
    );
  }

  return (
    <span className="prediction-create" data-testid="prediction-create">
      <select
        className="control-select"
        value={horizon}
        aria-label={t("predictions.horizon")}
        onChange={(e) => setHorizon(e.target.value)}
      >
        <option value="5D">{t("predictions.h5D")}</option>
        <option value="20D">{t("predictions.h20D")}</option>
        <option value="60D">{t("predictions.h60D")}</option>
      </select>
      <button
        type="button"
        className="control-btn"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {t("predictions.createConfirm")}
      </button>
      <button type="button" className="control-btn" onClick={() => setOpen(false)}>
        {t("common.cancel")}
      </button>
      {error && (
        <span className="status-error">
          {error === "prediction.underivable"
            ? t("predictions.underivable")
            : t(`errors.${error}`, { defaultValue: t("common.error") })}
        </span>
      )}
    </span>
  );
}
