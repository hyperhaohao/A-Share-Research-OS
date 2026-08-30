import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { formatArtifactType, uiLang } from "../presentation/enumLabels";

/**
 * 全库研究图谱 Canvas（UX Foundation UI7 / 任务书 §32）：
 * nodes + edges 直接进 React Flow；右侧 Inspector 展示选中节点并跳转原模块。
 * 默认上限 150 节点（后端有界），支持类型过滤。
 */

interface GraphArtifact {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
  created_at: string | null;
}

interface GraphData {
  nodes: GraphArtifact[];
  edges: Array<{ edge_id: string; from: string; to: string; relation: string }>;
}

const TYPE_COLOR: Record<string, string> = {
  research_run: "#2f6fa3",
  report: "#8a6f3f",
  report_version: "#b8b2a4",
  prediction: "#9a6b00",
  validation: "#2e7d54",
  experience_card: "#7c5cbf",
  workflow_run: "#5f8fbf",
  screening_run: "#bf7c5c",
  strategy_version: "#bf5f7c",
  review: "#5ba47e",
};

export function ResearchGraphCanvasPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [selected, setSelected] = useState<GraphArtifact | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const graphQuery = useQuery({
    queryKey: ["research-graph-canvas"],
    queryFn: async (): Promise<GraphData> => {
      const resp = await fetch("/api/v1/artifacts/graph?limit=150");
      if (!resp.ok) throw new Error("network.unreachable");
      return resp.json();
    },
  });

  const data = graphQuery.data;
  const types = useMemo(
    () => Array.from(new Set((data?.nodes ?? []).map((n) => n.artifact_type))).sort(),
    [data],
  );

  const filtered: GraphData = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    if (typeFilter === "all") return data;
    const keep = new Set(
      data.nodes.filter((n) => n.artifact_type === typeFilter).map((n) => n.artifact_id),
    );
    for (const e of data.edges) {
      if (keep.has(e.from)) keep.add(e.to);
      if (keep.has(e.to)) keep.add(e.from);
    }
    return {
      nodes: data.nodes.filter((n) => keep.has(n.artifact_id)),
      edges: data.edges.filter((e) => keep.has(e.from) && keep.has(e.to)),
    };
  }, [data, typeFilter]);

  const rfNodes: Node[] = useMemo(
    () =>
      filtered.nodes.map((n) => ({
        id: n.artifact_id,
        position: { x: hashPos(n.artifact_id, 0), y: hashPos(n.artifact_id, 1) },
        data: { label: `${formatArtifactType(n.artifact_type, lang)}\n${n.title.slice(0, 18)}` },
        style: {
          background: TYPE_COLOR[n.artifact_type] ?? "#888",
          color: "#fff",
          fontSize: 10,
          padding: 6,
          borderRadius: 6,
          width: 150,
        },
      })),
    [filtered, lang],
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      filtered.edges.map((e) => ({
        id: e.edge_id,
        source: e.from,
        target: e.to,
        label: e.relation,
        style: { stroke: "#98917f", width: 1 },
        labelStyle: { fontSize: 8 },
      })),
    [filtered],
  );

  return (
    <main className="page layout-canvas" data-testid="research-graph-canvas">
      <h1>{t("nav.researchGraph")}</h1>
      <div className="header-controls">
        <select
          className="control-select"
          value={typeFilter}
          aria-label={t("researchGraph.filter")}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="all">{t("researchGraph.filterAll")}</option>
          {types.map((tp) => (
            <option key={tp} value={tp}>
              {formatArtifactType(tp, lang)}
            </option>
          ))}
        </select>
        <span className="secondary">
          {t("researchGraph.canvasCount", { nodes: filtered.nodes.length, edges: filtered.edges.length })}
        </span>
      </div>

      {graphQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
      {graphQuery.data && filtered.nodes.length === 0 && (
        <p className="secondary">{t("researchGraph.empty")}</p>
      )}

      {filtered.nodes.length > 0 && (
        <div
          style={{ height: "calc(100vh - 260px)", border: "1px solid var(--color-border)", borderRadius: 8 }}
          data-testid="graph-canvas"
        >
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            fitView
            nodesDraggable
            panOnScroll
            minZoom={0.15}
            maxZoom={2}
            onNodeClick={(_, node) => {
              const found = filtered.nodes.find((n) => n.artifact_id === node.id);
              setSelected(found ?? null);
            }}
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable style={{ width: 140, height: 90 }} />
          </ReactFlow>
        </div>
      )}

      {selected && (
        <section className="card" data-testid="graph-inspector">
          <h2>{selected.title}</h2>
          <p className="secondary">{formatArtifactType(selected.artifact_type, lang)}</p>
          <div className="header-controls">
            <Link className="control-btn" to={selected.route || "#"}>
              {t("researchGraph.openArtifact")}
            </Link>
          </div>
        </section>
      )}
    </main>
  );
}

function hashPos(seed: string, axis: 0 | 1): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return ((h >>> (axis * 8)) % 1600) - 800 + (axis === 1 ? -200 : 0);
}
