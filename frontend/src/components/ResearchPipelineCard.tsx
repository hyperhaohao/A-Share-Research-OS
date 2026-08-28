import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

interface PipelineEvent {
  event: string;
  run_id?: string;
  capability?: string;
  status?: string;
  created?: number;
  analyst?: string;
  gate?: string;
  blocked?: boolean;
  report_id?: string;
  thesis_id?: string;
  claim_count?: number;
  [key: string]: unknown;
}

/** Human-readable stage labels for pipeline events (UX1). */
const STAGE_LABELS: Record<string, { zh: string; en: string }> = {
  run_started: { zh: "研究启动", en: "Research started" },
  source_progress: { zh: "数据采集", en: "Collecting data" },
  evidence_ready: { zh: "证据就绪", en: "Evidence ready" },
  snapshot_built: { zh: "证据快照", en: "Evidence snapshot" },
  quality_gate: { zh: "质量检查", en: "Quality gate" },
  analyst_progress: { zh: "分析", en: "Analysis" },
  claims_compiled: { zh: "主张汇总", en: "Claims compiled" },
  thesis_ready: { zh: "论点构建", en: "Thesis ready" },
  debate_ready: { zh: "多空辩论", en: "Debate ready" },
  valuation_ready: { zh: "估值计算", en: "Valuation ready" },
  scenario_ready: { zh: "情景分析", en: "Scenarios ready" },
  risk_ready: { zh: "风险评估", en: "Risk assessment" },
  report_ready: { zh: "报告生成", en: "Report ready" },
  run_completed: { zh: "研究完成", en: "Research completed" },
  run_failed: { zh: "研究失败", en: "Research failed" },
};

interface PipelineResult {
  events: PipelineEvent[];
  report_id: string;
  thesis_id?: string;
  claim_count?: number;
}

export function ResearchPipelineCard({ instrumentId }: { instrumentId: string }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const lang = i18n.language.startsWith("zh") ? "zh" : "en";

  const runPipeline = async (runId: string, signal: AbortSignal): Promise<PipelineResult> => {
    const resp = await fetch(
      `/api/v1/pipeline/run?instrument=${encodeURIComponent(instrumentId)}&run_id=${encodeURIComponent(runId)}`,
      { method: "POST", signal },
    );
    if (!resp.ok) {
      const body = (await resp.json().catch(() => null)) as { error_code?: string; detail?: string } | null;
      throw new Error(body?.error_code ?? body?.detail ?? "network.unreachable");
    }
    return resp.json();
  };

  const mutation = useMutation({
    mutationFn: async (runId: string) => runPipeline(runId, new AbortController().signal),
  });

  const start = () => {
    setEvents([]);
    setError(null);
    setRunning(true);
    setResult(null);
    const runId = `run_${crypto.randomUUID().slice(0, 12)}`;

    const source = new EventSource(`/api/v1/events/stream?run_id=${encodeURIComponent(runId)}`);
    source.addEventListener("run_completed", () => source.close());
    source.addEventListener("run_failed", () => source.close());

    mutation.mutate(runId, {
      onSuccess: (data) => {
        setEvents(data.events);
        setRunning(false);
        setResult(data);
        source.close();
      },
      onError: (err: Error) => {
        setError(err.message);
        setRunning(false);
        source.close();
      },
    });
  };

  // Group events into human-readable stages
  const stages = (() => {
    const seen = new Set<string>();
    return events
      .filter((e) => {
        const label = STAGE_LABELS[e.event];
        if (!label || seen.has(e.event)) return false;
        seen.add(e.event);
        return true;
      })
      .map((e) => {
        const label = STAGE_LABELS[e.event];
        return {
          event: e.event,
          label: lang === "zh" ? label.zh : label.en,
          detail: e.capability
            ? `${e.capability}${e.created !== undefined ? ` · ${e.created}` : ""}`
            : e.analyst ?? "",
        };
      });
  })();

  const reportId = result?.report_id ?? events.find((e) => e.report_id)?.report_id;

  return (
    <section className="card" data-testid="pipeline-card">
      <h2>{t("pipeline.title")}</h2>
      {!running && !result && (
        <button type="button" className="control-btn" onClick={start}>
          {t("pipeline.run")}
        </button>
      )}
      {running && <p className="mono">{t("common.loading")}</p>}
      {error && (
        <p className="status-error mono">
          {t(`errors.${error}`, { defaultValue: t("common.error") })}
        </p>
      )}

      {/* Human-readable stages */}
      {stages.length > 0 && (
        <ol data-testid="pipeline-stages">
          {stages.map((s, i) => (
            <li key={i} className="result-row">
              <span className="status-ok">✓</span>
              <span>{s.label}</span>
              {s.detail && <span className="secondary mono">{s.detail}</span>}
            </li>
          ))}
        </ol>
      )}

      {/* Final summary with CTAs */}
      {result && !running && (
        <div data-testid="pipeline-summary">
          {result.claim_count !== undefined && (
            <p className="mono">{t("pipeline.claimsCount", { count: result.claim_count })}</p>
          )}
          <div className="header-controls">
            {reportId && (
              <button
                type="button"
                className="control-btn"
                onClick={() => navigate(`/reports/${reportId}`)}
              >
                {t("pipeline.openReport")}
              </button>
            )}
            <button
              type="button"
              className="control-btn"
              onClick={() => navigate(`/instrument/${instrumentId}`)}
            >
              {t("pipeline.openWorkspace")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
