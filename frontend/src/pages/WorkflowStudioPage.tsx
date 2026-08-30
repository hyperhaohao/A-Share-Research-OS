import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

/**
 * Workflow Studio（任务书 §26 / UI7）：三栏布局
 * Node 库 / Canvas（React Flow DAG）/ Inspector（参数 + 运行控制）。
 * 当前 DAG 是固定序（Data→Rule→[Expression]→Validation→Output），
 * Inspector 编辑参数并发起运行。
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

const NODE_KIND_COLOR: Record<string, string> = {
  data: "#2f6fa3",
  rule: "#9a6b00",
  expression: "#7c5cbf",
  validation: "#2e7d54",
  output: "#8a6f3f",
};

export function WorkflowStudioPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [horizon, setHorizon] = useState("20");
  const [expression, setExpression] = useState("");

  const runsQuery = useQuery({
    queryKey: ["workflow-studio-runs"],
    queryFn: async (): Promise<WorkflowRun[]> => {
      const resp = await fetch("/api/v1/workflow-runs?limit=20");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: WorkflowRun[] };
      return body.results;
    },
    refetchInterval: 4000,
  });

  const runs = runsQuery.data ?? [];
  const selected = selectedRunId
    ? runs.find((r) => r.run_id === selectedRunId) ?? runs[0] ?? null
    : runs[0] ?? null;

  const launchM = useMutation({
    mutationFn: async (cardId: string) => {
      const resp = await fetch("/api/v1/workflow-runs/from-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          card_id: cardId,
          horizon_days: Number(horizon),
          expression: expression.trim() || undefined,
        }),
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      const body = (await resp.json()) as { run: WorkflowRun };
      setSelectedRunId(body.run.run_id);
      queryClient.invalidateQueries({ queryKey: ["workflow-studio-runs"] });
      return body.run;
    },
  });

  const dagNodes: Node[] = useMemo(() => {
    if (!selected) return [];
    return selected.nodes.map((n, i) => ({
      id: n.node_id,
      position: { x: 120 + i * 200, y: 150 },
      data: { label: `${n.title}\n${n.status}` },
      style: {
        background: NODE_KIND_COLOR[n.kind] ?? "#888",
        color: "#fff",
        padding: 8,
        borderRadius: 6,
        width: 160,
        fontSize: 10,
      },
    }));
  }, [selected]);

  const dagEdges: Edge[] = useMemo(() => {
    if (!selected) return [];
    const edges: Edge[] = [];
    for (let i = 1; i < selected.nodes.length; i++) {
      edges.push({
        id: `e-${selected.nodes[i - 1].node_id}-${selected.nodes[i].node_id}`,
        source: selected.nodes[i - 1].node_id,
        target: selected.nodes[i].node_id,
        animated: selected.nodes[i].status === "running",
      });
    }
    return edges;
  }, [selected]);

  return (
    <main className="page layout-canvas" data-testid="workflow-studio">
      <h1>{t("workflows.studioTitle")}</h1>
      <div className="studio-grid">
        <aside className="studio-left">
          <section className="card">
            <h3>{t("workflows.studioRuns")}</h3>
            <ul className="watch-list">
              {runs.map((r) => (
                <li
                  key={r.run_id}
                  className={`result-row${selected?.run_id === r.run_id ? " studio-active" : ""}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelectedRunId(r.run_id)}
                >
                  <span className="mono">{r.run_id.slice(3, 12)}</span>
                  <span className={r.status === "failed" ? "status-error" : r.status === "completed" ? "status-ok" : "secondary"}>
                    {t(`workflow.status.${r.status}`)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <section className="card">
            <h3>{t("workflows.studioInspector")}</h3>
            {selected ? (
              <div className="task-grid">
                <span>{t("workflow.horizon")}</span>
                <input
                  className="control-input"
                  data-testid="studio-horizon"
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                />
                <span>{t("workflow.expressionLabel")}</span>
                <input
                  className="control-input"
                  data-testid="studio-expression"
                  value={expression}
                  placeholder={t("workflow.expressionPlaceholder")}
                  onChange={(e) => setExpression(e.target.value)}
                />
                <button
                  type="button"
                  className="control-btn"
                  data-testid="studio-launch"
                  disabled={launchM.isPending || !selected.card_id}
                  onClick={() => {
                    if (selected.card_id) launchM.mutate(selected.card_id);
                  }}
                >
                  {t("workflow.launch")}
                </button>
              </div>
            ) : (
              <p className="secondary">{t("workflows.studioSelectRun")}</p>
            )}
          </section>
        </aside>

        <div className="studio-canvas" data-testid="studio-canvas">
          {selected && dagNodes.length > 0 ? (
            <ReactFlow
              nodes={dagNodes}
              edges={dagEdges}
              fitView
              minZoom={0.4}
              maxZoom={1.5}
              proOptions={{ hideAttribution: true }}
            >
              <Background />
              <Controls showInteractive={false} />
            </ReactFlow>
          ) : (
            <div className="empty-state">
              <p>{t("workflows.studioNoDag")}</p>
              <p className="secondary">{t("workflows.emptyHint")}</p>
            </div>
          )}
        </div>

        <aside className="studio-right">
          {selected && selected.status !== "running" && (
            <section className="card">
              <h3>{t("workflows.studioMetrics")}</h3>
              <pre className="mono secondary" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
                {JSON.stringify(selected.metrics, null, 2)}
              </pre>
              {selected.error && <p className="status-error">{selected.error}</p>}
            </section>
          )}
        </aside>
      </div>
    </main>
  );
}
