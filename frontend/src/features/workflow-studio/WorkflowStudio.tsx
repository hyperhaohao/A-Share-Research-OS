import { useCallback, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Background,
  Controls,
  ReactFlow,
  type Connection,
  type Edge as RfEdge,
  type Node as RfNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useTranslation } from "react-i18next";
import { Badge, Button, Panel } from "../../ui/guanlan";
import { NODE_SPECS, validateGraphClient, type DefinitionSummary, type DefEdge, type DefNode } from "./spec";
import { WorkflowNodeLibrary } from "./WorkflowNodeLibrary";
import { WorkflowInspector } from "./WorkflowInspector";
import { WorkflowRunPanel, useWorkflowRuns, type WorkflowRun } from "./WorkflowRunPanel";

/**
 * Workflow Studio — 真正的 Editor（Guanlan Direct Port G4，方案 §15/§35）：
 * Node Library / Canvas（可增删节点、可连线）/ Inspector（按 schema 编辑参数）/
 * Toolbar（命名、存版本、运行）/ 运行控制与指标区。不再是 Run Viewer。
 * 图定义经 /workflow-definitions 版本化落库，运行走 /workflow-definitions/{id}/run。
 */

function useDefinitions() {
  return useQuery({
    queryKey: ["studio-definitions"],
    queryFn: async (): Promise<DefinitionSummary[]> => {
      const resp = await fetch("/api/v1/workflow-definitions?limit=20");
      if (!resp.ok) return [];
      const body = (await resp.json()) as { results: DefinitionSummary[] };
      return body.results;
    },
  });
}

export function WorkflowStudio() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [nodes, setNodes] = useState<DefNode[]>([]);
  const [edges, setEdges] = useState<DefEdge[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [defId, setDefId] = useState<string | null>(null);
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const keySeq = useRef(0);

  const runsQuery = useWorkflowRuns();
  const runs = runsQuery.data ?? [];
  const selectedRun: WorkflowRun | null = useMemo(() => {
    const id = selectedRunId ?? lastRunId;
    return runs.find((r) => r.run_id === id) ?? null;
  }, [runs, selectedRunId, lastRunId]);

  const selected = nodes.find((n) => n.key === selectedKey) ?? null;

  const addNode = (kind: string) => {
    keySeq.current += 1;
    const n = keySeq.current;
    const spec = NODE_SPECS[kind];
    const node: DefNode = {
      key: `${kind}_${n}`,
      kind,
      title: null,
      params: Object.fromEntries(spec.params.map((p) => [p.id, p.defaultValue])),
    };
    setNodes((prev) => [...prev, node]);
    setSelectedKey(node.key);
    setError(null);
  };

  const updateNode = (next: DefNode) => {
    setNodes((prev) => prev.map((x) => (x.key === next.key ? next : x)));
  };

  const deleteNode = () => {
    if (!selected) return;
    setNodes((prev) => prev.filter((n) => n.key !== selected.key));
    setEdges((prev) => prev.filter((e) => e.from !== selected.key && e.to !== selected.key));
    setSelectedKey(null);
  };

  const clientError = validateGraphClient(nodes, edges);

  const saveMutation = useMutation({
    mutationFn: async (): Promise<{ defId: string; versionNo: number }> => {
      const graphError = validateGraphClient(nodes, edges);
      if (graphError) throw new Error(graphError);
      const payload = {
        name: name.trim() || t("studio.defaultName"),
        instrument_id: null,
        nodes: nodes.map((n) => ({ key: n.key, kind: n.kind, title: n.title, params: n.params })),
        edges,
      };
      const url = defId
        ? `/api/v1/workflow-definitions/${defId}/versions`
        : "/api/v1/workflow-definitions";
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          defId ? { nodes: payload.nodes, edges: payload.edges, note: null } : payload,
        ),
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      if (defId) {
        const body = (await resp.json()) as { version: { def_id: string; version_no: number } };
        return { defId: body.version.def_id, versionNo: body.version.version_no };
      }
      const body = (await resp.json()) as {
        definition: { def_id: string; current_version: number };
      };
      return { defId: body.definition.def_id, versionNo: body.definition.current_version };
    },
    onSuccess: (saved) => {
      setDefId(saved.defId);
      setSavedVersion(saved.versionNo);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["studio-definitions"] });
    },
    onError: (e) => setError(e instanceof Error ? e.message : "common.error"),
  });

  const runMutation = useMutation({
    mutationFn: async (): Promise<string> => {
      if (!defId) throw new Error("studio.err.saveFirst");
      const resp = await fetch(`/api/v1/workflow-definitions/${defId}/run`, { method: "POST" });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(err?.error_code ?? "network.unreachable");
      }
      const body = (await resp.json()) as { run: WorkflowRun };
      return body.run.run_id;
    },
    onSuccess: (runId) => {
      setLastRunId(runId);
      setSelectedRunId(runId);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["workflow-studio-runs"] });
    },
    onError: (e) => setError(e instanceof Error ? e.message : "common.error"),
  });

  // 图 → React Flow（按连接深度分列的网格布局）
  const rfNodes: RfNode[] = useMemo(() => {
    const depth = new Map<string, number>();
    nodes.forEach((n) => depth.set(n.key, 0));
    for (let i = 0; i < nodes.length; i += 1) {
      for (const e of edges) {
        const d = depth.get(e.from);
        if (d != null && (depth.get(e.to) ?? 0) < d + 1) depth.set(e.to, d + 1);
      }
    }
    const columnRows = new Map<number, number>();
    return nodes.map((n) => {
      const d = depth.get(n.key) ?? 0;
      const row = columnRows.get(d) ?? 0;
      columnRows.set(d, row + 1);
      const spec = NODE_SPECS[n.kind];
      const summary = Object.entries(n.params)
        .filter(([, v]) => v !== "" && v != null)
        .slice(0, 3)
        .map(([k, v]) => `${k}=${v}`)
        .join("\n");
      return {
        id: n.key,
        position: { x: 40 + d * 250, y: 40 + row * 140 },
        data: { label: `${n.title || t(spec.titleKey)}${summary ? `\n${summary}` : ""}` },
        style: {
          background: "var(--color-bg-elevated)",
          border: `2px solid ${spec.color}`,
          borderRadius: 6,
          padding: 8,
          width: 180,
          fontSize: 11,
          color: "var(--color-text)",
          whiteSpace: "pre-line",
        },
      } satisfies RfNode;
    });
  }, [nodes, edges, t]);

  const rfEdges: RfEdge[] = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e${i}-${e.from}-${e.to}`,
        source: e.from,
        target: e.to,
      })),
    [edges],
  );

  const onConnect = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) {
      return;
    }
    setEdges((prev) => {
      if (prev.some((e) => e.from === connection.source && e.to === connection.target)) {
        return prev;
      }
      return [...prev, { from: connection.source, to: connection.target }];
    });
    setError(null);
  }, []);

  const loadDefinition = async (defIdToLoad: string) => {
    const resp = await fetch(`/api/v1/workflow-definitions/${defIdToLoad}`);
    if (!resp.ok) return;
    const body = (await resp.json()) as {
      definition: { def_id: string; name: string; current_version: number; nodes: DefNode[]; edges: DefEdge[] };
    };
    setDefId(body.definition.def_id);
    setName(body.definition.name);
    setNodes(body.definition.nodes ?? []);
    setEdges(body.definition.edges ?? []);
    setSavedVersion(body.definition.current_version);
    setSelectedKey(null);
    setError(null);
  };

  const definitionsQuery = useDefinitions();

  return (
    <main className="page layout-canvas" data-testid="workflow-studio">
      <div className="ws-toolbar">
        <h1 className="ws-title">{t("studio.title")}</h1>
        <input
          className="control-input ws-name"
          value={name}
          placeholder={t("studio.namePlaceholder")}
          onChange={(e) => setName(e.target.value)}
        />
        <Button
          variant="primary"
          data-testid="studio-save"
          disabled={saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          {defId ? t("studio.saveVersion") : t("studio.save")}
        </Button>
        {defId && savedVersion != null && (
          <Badge tone="neutral">v{savedVersion}</Badge>
        )}
        <Button
          variant="primary"
          data-testid="studio-run"
          disabled={runMutation.isPending || !defId}
          onClick={() => runMutation.mutate()}
        >
          {t("studio.run")} ▶
        </Button>
        {!defId && <span className="secondary">{t("studio.err.saveFirst")}</span>}
        {error && (
          <span className="status-error">
            {t(`errors.${error}`, { defaultValue: t("common.error") })}
          </span>
        )}
        {clientError && !error && <span className="secondary">{t(clientError)}</span>}
      </div>

      <div className="studio-grid ws-grid">
        <aside className="studio-left ws-left">
          <Panel title={t("studio.libraryTitle")}>
            <WorkflowNodeLibrary onAdd={addNode} />
          </Panel>
          <Panel title={t("studio.definitionsTitle")} hint={`${definitionsQuery.data?.length ?? 0}`}>
            <ul className="watch-list">
              {(definitionsQuery.data ?? []).map((d) => (
                <li key={d.def_id} className="result-row">
                  <button
                    type="button"
                    className="cc-session-link"
                    onClick={() => void loadDefinition(d.def_id)}
                  >
                    {d.name}
                  </button>
                  <span className="secondary mono">v{d.current_version}</span>
                </li>
              ))}
              {(definitionsQuery.data ?? []).length === 0 && (
                <li className="secondary">{t("studio.noDefinitions")}</li>
              )}
            </ul>
          </Panel>
        </aside>

        <div className="studio-canvas" data-testid="studio-canvas">
          {nodes.length > 0 ? (
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              onConnect={onConnect}
              onNodeClick={(_, node) => setSelectedKey(node.id)}
              onPaneClick={() => setSelectedKey(null)}
              deleteKeyCode={["Backspace", "Delete"]}
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
              <p>{t("studio.canvasEmpty")}</p>
              <p className="secondary">{t("studio.canvasHint")}</p>
            </div>
          )}
        </div>

        <aside className="studio-right ws-right">
          <WorkflowInspector node={selected} onChange={updateNode} onDelete={deleteNode} />
          <WorkflowRunPanel run={selectedRun} onSelect={(id) => setSelectedRunId(id)} />
        </aside>
      </div>
    </main>
  );
}
