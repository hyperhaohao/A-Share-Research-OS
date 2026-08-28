import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

/**
 * Report → [生成预测] → PredictionBuilder (PW2 §17).
 * Refusals (422 prediction.underivable) surface the honest reason.
 */
export function PredictionCreateButton({ reportId }: { reportId: string }) {
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
      return resp.json() as Promise<{ prediction: { prediction_id: string } }>;
    },
    onSuccess: () => navigate("/predictions"),
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
