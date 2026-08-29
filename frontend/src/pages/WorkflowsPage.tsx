import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatWhen } from "../presentation/format";

/**
 * 研究验证工作流（任务书 §26）：独立模块 + 一级导航。
 * 工作流从经验卡发起；此处为运行列表与运行详情（数据来自 /workflow-runs）。
 */

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
  instrument_id: string;
  status: string;
  params: Record<string, unknown>;
  nodes: WfNode[];
  metrics: Record<string, unknown>;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export function WorkflowsPage() {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["workflow-runs-all"],
    queryFn: async (): Promise<WorkflowRun[]> => {
      const resp = await fetch("/api/v1/workflow-runs?limit=30");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: WorkflowRun[] };
      return body.results;
    },
  });

  return (
    <main className="page layout-workspace" data-testid="workflows-page">
      <h1>{t("nav.workflows")}</h1>
      <p className="secondary">{t("workflows.pageHint")}</p>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && (
        <div className="empty-state" data-testid="workflows-empty">
          <p>{t("workflows.emptyTitle")}</p>
          <p className="secondary">{t("workflows.emptyHint")}</p>
          <Link className="control-btn" to="/experience">
            {t("workflows.emptyAction")}
          </Link>
        </div>
      )}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((run) => (
            <li className="result-row" key={run.run_id} data-testid="workflow-row">
              <span className="mono">{run.run_id}</span>
              <span className={run.status === "failed" ? "status-error" : run.status === "completed" ? "status-ok" : "secondary"}>
                {t(`workflow.status.${run.status}`)}
              </span>
              <span className="secondary">{formatWhen(run.updated_at, "zh")}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export function WorkflowDetailPage() {
  const params = useParams();
  const runId = params.runId ?? "";
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["workflow-run-detail", runId],
    enabled: runId !== "",
    refetchInterval: 2000,
    queryFn: async (): Promise<WorkflowRun> => {
      const resp = await fetch(`/api/v1/workflow-runs/${runId}`);
      if (!resp.ok) throw new Error("workflow.not_found");
      const body = (await resp.json()) as { run: WorkflowRun };
      return body.run;
    },
  });

  if (isPending) {
    return (
      <main className="page layout-workspace" data-testid="workflow-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError || !data) {
    return (
      <main className="page layout-workspace" data-testid="workflow-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  return (
    <main className="page layout-workspace" data-testid="workflow-detail">
      <p>
        <Link to="/workflows" className="secondary">← {t("nav.workflows")}</Link>
      </p>
      <h1 className="mono">{data.run_id}</h1>
      <p className="secondary">
        {t("workflow.statusLabel")}: {t(`workflow.status.${data.status}`)}
      </p>
      <ul className="watch-list">
        {data.nodes.map((n) => (
          <li className="result-row" key={n.node_id}>
            <span className={n.status === "ok" ? "status-ok" : n.status === "failed" ? "status-error" : "secondary"}>
              {n.status}
            </span>
            <span>{n.title}</span>
            {n.detail && <span className="secondary">{n.detail}</span>}
            {n.error && <span className="status-error">{n.error}</span>}
          </li>
        ))}
      </ul>
    </main>
  );
}
