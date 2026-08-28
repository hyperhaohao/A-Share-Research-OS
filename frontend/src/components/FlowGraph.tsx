/**
 * React Flow research graph (整改 R4.6): zoom / pan / filter / node detail /
 * theme + i18n. Columnar view retained as fallback.
 */

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import "@xyflow/react/dist/style.css";

interface GraphNode {
  node_id: string;
  kind: string;
  label: string;
}
interface GraphEdge {
  src: string;
  dst: string;
  relation: string;
}

const KIND_ORDER = [
  "source",
  "evidence",
  "snapshot",
  "claim",
  "thesis",
  "research_run",
  "report",
  "report_version",
];

/** Layout by research layer (column index) — simple, deterministic. */
function layout(graph: { nodes: GraphNode[]; edges: GraphEdge[] }): {
  nodes: Node[];
  edges: Edge[];
} {
  const level = new Map<string, number>();
  graph.nodes.forEach((n) => {
    const idx = KIND_ORDER.indexOf(n.kind);
    level.set(n.node_id, idx >= 0 ? idx : KIND_ORDER.length);
  });
  // nudge: a node is at least one past its upstream
  for (let pass = 0; pass < 3; pass++) {
    graph.edges.forEach((e) => {
      const up = level.get(e.src) ?? 0;
      const down = level.get(e.dst) ?? 0;
      if (down <= up) level.set(e.dst, up + 1);
    });
  }
  const byLevel = new Map<number, GraphNode[]>();
  graph.nodes.forEach((n) => {
    const lv = level.get(n.node_id) ?? 0;
    if (!byLevel.has(lv)) byLevel.set(lv, []);
    byLevel.get(lv)!.push(n);
  });
  const nodes: Node[] = [];
  byLevel.forEach((list, lv) => {
    list.forEach((n, i) => {
      nodes.push({
        id: n.node_id,
        position: { x: lv * 260, y: i * 84 },
        data: { label: `[${n.kind}] ${n.label.slice(0, 60)}` },
        style: {
          background: "var(--color-bg-elevated)",
          color: "var(--color-text)",
          border: "1px solid var(--color-border)",
          borderRadius: 6,
          fontSize: 11,
          padding: 6,
        },
      });
    });
  });
  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e${i}`,
    source: e.src,
    target: e.dst,
    label: e.relation,
    style: { stroke: "var(--color-border)", fontSize: 9 },
    labelStyle: { fill: "var(--color-text-secondary)", fontSize: 9 },
  }));
  return { nodes, edges };
}

export function FlowGraphTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const [kindFilter, setKindFilter] = useState<string>("all");
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [trace, setTrace] = useState<
    | {
        direction: string;
        nodes: Array<{ node_id: string; kind: string; depth: number }>;
        edges: Array<{ src: string; dst: string; relation: string }>;
      }
    | null
  >(null);

  const { data, isPending, isError } = useQuery({
    queryKey: ["graph", instrumentId],
    queryFn: () =>
      fetchJson<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
        `/api/v1/graph?instrument=${encodeURIComponent(instrumentId)}`,
      ),
  });

  const filtered = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    if (kindFilter === "all") return data;
    const keep = new Set(
      data.nodes
        .filter((n) => n.kind === kindFilter)
        .flatMap((n) => [n.node_id, ...graph_neighbors(data, n.node_id)])
    );
    return {
      nodes: data.nodes.filter((n) => keep.has(n.node_id)),
      edges: data.edges.filter((e) => keep.has(e.src) && keep.has(e.dst)),
    }
  }, [data, kindFilter]);

  const { nodes, edges } = useMemo(() => layout(filtered), [filtered]);

  const onNodeClick = (_: unknown, node: Node) => {
    const graphNode = data?.nodes.find((n) => n.node_id === node.id);
    setSelected(graphNode ?? null);
    setTrace(null);
  };

  const runTrace = async (direction: "upstream" | "downstream") => {
    if (!selected) return;
    const body = await fetchJson<{
      nodes: Array<{ node_id: string; kind: string; depth: number }>;
      edges: Array<{ src: string; dst: string; relation: string }>;
    }>(
      `/api/v1/graph/trace?instrument=${encodeURIComponent(instrumentId)}&node_id=${encodeURIComponent(
        selected.node_id,
      )}&direction=${direction}`,
    );
    setTrace({ direction, nodes: body.nodes, edges: body.edges });
  };

  if (isPending) return <p className="mono">{t("common.loading")}</p>;
  if (isError) return <p className="status-error">{t("common.error")}</p>;

  const kinds = [...new Set((data?.nodes ?? []).map((n) => n.kind))];
  return (
    <div>
      <div className="header-controls" style={{ marginBottom: 8 }}>
        <select
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value)}
          aria-label={t("workspace.filter")}
          className="control-btn"
        >
          <option value="all">{t("workspace.filterAll")}</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </div>

      <div style={{ height: 480, border: "1px solid var(--color-border)", borderRadius: 8 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          nodesDraggable
          panOnScroll
          minZoom={0.2}
          maxZoom={2}
          onNodeClick={onNodeClick}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable style={{ width: 140, height: 90 }} />
        </ReactFlow>
      </div>

      {selected && (
        <div className="card" data-testid="graph-node-detail">
          <h3>
            <span className="mono">[{selected.kind}]</span> {selected.label}
          </h3>
          <div className="header-controls">
            <button className="control-btn" onClick={() => runTrace("upstream")}>
              {t("workspace.upstream")}
            </button>
            <button className="card-btn" onClick={() => runTrace("downstream")}>
              {t("workspace.downstream")}
              </button>
            <button className="control-btn" onClick={() => setTrace(null)}>
              {t("workspace.close")}
            </button>
          </div>
          {trace && (
            <div data-testid="graph-trace">
              <p className="mono secondary">
                {trace.direction} · {trace.nodes.length} nodes
              </p>
              <ul>
                {trace.nodes.map((n) => (
                  <li key={n.node_id}>
                    <span className="mono">[{n.kind}]</span> depth {n.depth}{" "}
                    <span className="mono secondary">{n.node_id.slice(0, 26)}</span>
                    </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function graph_neighbors(graph: { nodes: GraphNode[]; edges: GraphEdge[] }, node_id: string): string[] {
  const out: string[] = [];
  graph.edges.forEach((e) => {
    if (e.src === node_id) out.push(e.dst);
    if (e.dst === node_id) out.push(e.src);
  });
  return out;
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`http_${resp.status}`);
  return resp.json();
}
