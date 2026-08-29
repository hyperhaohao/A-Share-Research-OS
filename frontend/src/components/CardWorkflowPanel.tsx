import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface WfNode {
  node_id: string;
  kind: string;
  title: string;
  status: string;
  detail: string | null;
  error: string | null;
}

interface WorkflowRun {
  run_id: string;
  card_id: string | null;
  status: string;
  params: Record<string, unknown>;
  nodes: WfNode[];
  metrics: Record<string, unknown>;
  error: string | null;
}

const NODE_STATUS_KEY: Record<string, string> = {
  pending: "workflow.stepPending",
  running: "workflow.stepRunning",
  ok: "workflow.stepOk",
  failed: "workflow.stepFailed",
};

/**
 * 经验卡 → 验证工作流（§44/§73）：发起最小强类型 DAG
 * Data(真实日线) → Rule(前向收益) → Validation(指标) → Output(落库)。
 */
export function CardWorkflowPanel({ cardId }: { cardId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [horizon, setHorizon] = useState("20");
  const [runId, setRunId] = useState<string | null>(null);

  const lastRunQuery = useQuery({
    queryKey: ["workflow-runs", cardId],
    queryFn: async (): Promise<WorkflowRun | null> => {
      const resp = await fetch(`/api/v1/workflow-runs?card_id=${cardId}&limit=1`);
      if (!resp.ok) return null;
      const body = (await resp.json()) as { results: WorkflowRun[] };
      return body.results[0] ?? null;
    },
  });

  const runQuery = useQuery({
    queryKey: ["workflow-run", runId],
    enabled: runId != null,
    refetchInterval: runId ? 1200 : false,
    queryFn: async (): Promise<WorkflowRun> => {
      const resp = await fetch(`/api/v1/workflow-runs/${runId}`);
      if (!resp.ok) throw new Error("workflow.not_found");
      const body = (await resp.json()) as { run: WorkflowRun };
      return body.run;
    },
  });

  const launchM = useMutation({
    mutationFn: async () => {
      const resp = await fetch("/api/v1/workflow-runs/from-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId, horizon_days: Number(horizon) }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "network.unreachable");
      }
      const body = (await resp.json()) as { run: WorkflowRun };
      setRunId(body.run.run_id);
      queryClient.invalidateQueries({ queryKey: ["workflow-runs", cardId] });
    },
  });

  const run = runId ? runQuery.data : lastRunQuery.data ?? null;
  const done = run && run.status !== "running";

  return (
    <section className="card" data-testid="workflow-panel">
      <h2>{t("workflow.title")}</h2>
      <p className="secondary">{t("workflow.hint")}</p>
      <div className="header-controls">
        <select
          className="control-select"
          aria-label={t("workflow.horizon")}
          data-testid="workflow-horizon"
          value={horizon}
          onChange={(e) => setHorizon(e.target.value)}
        >
          <option value="5">{t("workflow.h5")}</option>
          <option value="20">{t("workflow.h20")}</option>
          <option value="60">{t("workflow.h60")}</option>
        </select>
        <button
          type="button"
          className="control-btn"
          data-testid="workflow-launch"
          disabled={launchM.isPending || (run?.status === "running")}
          onClick={() => launchM.mutate()}
        >
          {t("workflow.launch")}
        </button>
      </div>

      {run && (
        <div className="plan-steps" data-testid="workflow-run">
          <ul className="result-list">
            {run.nodes.map((n) => (
              <li
                key={n.node_id}
                className={`plan-step stage-${n.status === "ok" ? "done" : n.status}`}
              >
                <span className="plan-step-status">
                  {t(NODE_STATUS_KEY[n.status] ?? n.status)}
                </span>
                <span className="plan-step-title">{n.title}</span>
                {n.detail && <span className="secondary">{n.detail}</span>}
                {n.error && <span className="status-error">{n.error}</span>}
              </li>
            ))}
          </ul>
          {run.status === "running" && <p className="secondary">{t("workflow.running")}</p>}
          {run.status === "failed" && (
            <p className="status-error">{t("workflow.failed")}: {run.error}</p>
          )}
          {run.status === "completed" && <p className="status-ok">{t("workflow.completed")}</p>}
          {done && run.metrics && <MetricsGrid metrics={run.metrics} />}
        </div>
      )}
      {!run && <p className="secondary">{t("workflow.noRuns")}</p>}
    </section>
  );
}

function MetricsGrid({ metrics }: { metrics: Record<string, unknown> }) {
  const { t } = useTranslation();
  const num = (v: unknown, suffix = "") =>
    v == null ? "—" : `${v}${suffix}`;
  return (
    <div className="task-grid" data-testid="workflow-metrics">
      <span>{t("workflow.samples")}</span>
      <span className="mono">{num(metrics.samples)}</span>
      <span>{t("workflow.hitRate")}</span>
      <span className="mono">{num(metrics.hit_rate_pct, "%")}</span>
      <span>{t("workflow.avgReturn")}</span>
      <span className="mono">{num(metrics.avg_return_pct, "%")}</span>
      <span>{t("workflow.worst")}</span>
      <span className="mono">{num(metrics.worst_return_pct, "%")}</span>
      <span>{t("workflow.best")}</span>
      <span className="mono">{num(metrics.best_return_pct, "%")}</span>
    </div>
  );
}
