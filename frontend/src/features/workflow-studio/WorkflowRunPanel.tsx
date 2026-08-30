import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Badge, Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";

interface WfNode {
  node_id: string;
  kind: string;
  title: string;
  status: string;
  detail: string | null;
  error: string | null;
}

export interface WorkflowRun {
  run_id: string;
  card_id: string | null;
  instrument_id: string;
  kind: string;
  status: string;
  params: Record<string, unknown>;
  nodes: WfNode[];
  metrics: Record<string, unknown>;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * 运行控制 + 指标区（方案 §15 运行控制/运行状态/错误状态/指标区）：
 * 运行列表 + 选中运行的节点逐项状态（donor 逐节点点灯）+ 指标 + 错误显形。
 */
export function useWorkflowRuns(intervalMs = 4000) {
  return useQuery({
    queryKey: ["workflow-studio-runs"],
    queryFn: async (): Promise<WorkflowRun[]> => {
      const resp = await fetch("/api/v1/workflow-runs?limit=20");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: WorkflowRun[] };
      return body.results;
    },
    refetchInterval: intervalMs,
  });
}

export function WorkflowRunPanel({
  run,
  onSelect,
}: {
  run: WorkflowRun | null;
  onSelect: (runId: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const runsQuery = useWorkflowRuns();
  const runs = runsQuery.data ?? [];

  return (
    <Panel title={t("studio.runsTitle")} hint={`${runs.length}`}>
      <ul className="watch-list ws-run-list" data-testid="studio-runs">
        {runs.map((r) => (
          <li
            key={r.run_id}
            className={`result-row${run?.run_id === r.run_id ? " studio-active" : ""}`}
            onClick={() => onSelect(r.run_id)}
          >
            <button type="button" className="cc-session-link">
              {r.kind === "definition"
                ? t("studio.runKindDefinition")
                : t("studio.runKindCard")}
            </button>
            <span
              className={
                r.status === "failed"
                  ? "status-error"
                  : r.status === "completed"
                    ? "status-ok"
                    : "secondary"
              }
            >
              {t(`workflow.status.${r.status}`)}
            </span>
            <span className="secondary">{formatWhen(r.created_at, lang)}</span>
          </li>
        ))}
        {runs.length === 0 && <li className="secondary">{t("studio.noRuns")}</li>}
      </ul>

      {run && (
        <div className="ws-run-detail" data-testid="studio-run-detail">
          <div className="ws-run-nodes">
            {run.nodes.map((n) => (
              <div key={n.node_id} className="ws-run-node" data-status={n.status}>
                <span className="ws-run-node-dot" />
                <span className="ws-run-node-title">{n.title}</span>
                {n.error && <span className="status-error ws-run-node-err">{n.error}</span>}
                {!n.error && n.detail && (
                  <span className="secondary ws-run-node-detail">{n.detail}</span>
                )}
              </div>
            ))}
          </div>
          {run.status === "completed" && (
            <div className="ws-run-metrics" data-testid="studio-run-metrics">
              {[
                ["samples", run.metrics.samples],
                ["hit_rate_pct", run.metrics.hit_rate_pct],
                ["avg_return_pct", run.metrics.avg_return_pct],
                ["best_return_pct", run.metrics.best_return_pct],
                ["worst_return_pct", run.metrics.worst_return_pct],
              ].map(([k, v]) => (
                <div key={String(k)} className="cc-brief-cell">
                  <div className="cc-brief-label">{String(k)}</div>
                  <div className="num">{v == null ? "—" : String(v)}</div>
                </div>
              ))}
              {run.metrics.expression_verdict != null && (
                <div className="cc-brief-cell">
                  <div className="cc-brief-label">{t("studio.exprVerdict")}</div>
                  <Badge tone={run.metrics.expression_verdict ? "ok" : "error"}>
                    {run.metrics.expression_verdict ? t("studio.exprTrue") : t("studio.exprFalse")}
                  </Badge>
                </div>
              )}
            </div>
          )}
          {run.error && <p className="status-error">{run.error}</p>}
        </div>
      )}

    </Panel>
  );
}
