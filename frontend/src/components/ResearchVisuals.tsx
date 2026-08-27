import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

interface TimelineEvent {
  occurred_at: string;
  kind: string;
  title: string;
  ref_id: string;
  detail: Record<string, unknown>;
}

export function TimelineTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const [kindFilter, setKindFilter] = useState<string>("");

  const kinds = ["market_event", "evidence_added", "claim_changed", "thesis_changed", "corporate_event", "research_run", "snapshot_built", "report_version"];

  const { data, isPending } = useQuery({
    queryKey: ["timeline", instrumentId, kindFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ instrument: instrumentId });
      if (kindFilter) params.set("kinds", kindFilter);
      const resp = await fetch(`/api/v1/timeline?${params}`);
      if (!resp.ok) throw new Error("network.unreachable");
      return resp.json() as Promise<{ results: TimelineEvent[] }>;
    },
  });

  return (
    <div data-testid="timeline-tab">
      <div className="kind-filters" role="group" aria-label={t("timeline.filter")}>
        <button
          type="button"
          className={kindFilter === "" ? "control-btn active" : "control-btn"}
          onClick={() => setKindFilter("")}
        >
          {t("timeline.all")}
        </button>
        {kinds.map((k) => (
          <button
            key={k}
            type="button"
            className={kindFilter === k ? "control-btn active" : "control-btn"}
            onClick={() => setKindFilter(k)}
          >
            {t(`timeline.kind.${k}`)}
          </button>
        ))}
      </div>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {data && (
        <ul className="timeline-list">
          {data.results.map((e) => (
            <li key={`${e.kind}-${e.ref_id}`} className="timeline-item">
              <span className="mono secondary">{e.occurred_at.slice(0, 16).replace("T", " ")}</span>
              <span className="timeline-kind mono">{t(`timeline.kind.${e.kind}`)}</span>
              <span>{e.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

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
interface TraceResult {
  nodes: Array<{ node_id: string; kind: string; label: string; depth: number }>;
  edges: Array<{ src: string; dst: string; relation: string }>;
}

const KIND_ORDER = ["source", "evidence", "snapshot", "claim", "thesis", "research_run", "report", "report_version"];

export function GraphTab({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);

  const { data, isPending } = useQuery({
    queryKey: ["graph", instrumentId],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/graph?instrument=${encodeURIComponent(instrumentId)}`);
      if (!resp.ok) throw new Error("network.unreachable");
      return resp.json() as Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }>;
    },
  });

  const columns = useMemo(() => {
    const byKind = new Map<string, GraphNode[]>();
    for (const n of data?.nodes ?? []) {
      const list = byKind.get(n.kind) ?? [];
      list.push(n);
      byKind.set(n.kind, list);
    }
    return KIND_ORDER.filter((k) => byKind.has(k)).map((k) => ({ kind: k, nodes: byKind.get(k)! }));
  }, [data]);

  const traceNode = async (nodeId: string, direction: "upstream" | "downstream") => {
    const resp = await fetch(
      `/api/v1/graph/trace?instrument=${encodeURIComponent(instrumentId)}&node_id=${encodeURIComponent(nodeId)}&direction=${direction}`,
    );
    if (!resp.ok) return;
    setTrace(await resp.json());
    setSelected(nodeId);
  };

  return (
    <div data-testid="graph-tab">
      <p className="secondary">{t("graph.hint")}</p>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      <div className="graph-columns">
        {columns.map(({ kind, nodes }) => (
          <div key={kind} className="graph-column" data-kind={kind}>
            <h3 className="mono secondary">{t(`graph.kind.${kind}`)}</h3>
            {nodes.map((n) => (
              <button
                key={n.node_id}
                type="button"
                className={selected === n.node_id ? "graph-node selected" : "graph-node"}
                onClick={() => traceNode(n.node_id, "upstream")}
                title={n.label}
              >
                {n.label.slice(0, 42)}
              </button>
            ))}
          </div>
        ))}
      </div>
      {trace && (
        <div className="card" data-testid="trace-result">
          <h2>
            {t("graph.trace")} · {trace.nodes[0]?.label}
          </h2>
          <ul>
            {trace.nodes.map((n) => (
              <li key={n.node_id} className="mono">
                <span className="secondary">{n.depth}</span> [{n.kind}] {n.label}
              </li>
            ))}
          </ul>
          <button type="button" className="control-btn" onClick={() => { setTrace(null); setSelected(null); }}>
            {t("graph.close")}
          </button>
        </div>
      )}
    </div>
  );
}
