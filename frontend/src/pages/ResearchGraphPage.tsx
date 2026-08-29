import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatArtifactType, formatRelation, uiLang } from "../presentation/enumLabels";

/**
 * 全库研究图谱（V2 Phase I, 总纲 §78）：Phase A 起积累的 Artifact/Edge
 * 全库视图 + Lineage Explorer。任一节点可溯源、可跳转。
 */

interface GraphNode {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
  instrument_ids: string[];
  created_at: string | null;
}

interface GraphEdge {
  edge_id: string;
  from: string;
  to: string;
  relation: string;
}

interface LineageNode {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
  relation: string;
  depth: number;
}

export function ResearchGraphPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const graphQuery = useQuery({
    queryKey: ["research-graph"],
    queryFn: async (): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> => {
      const resp = await fetch("/api/v1/artifacts/graph?limit=150");
      if (!resp.ok) throw new Error("network.unreachable");
      return resp.json();
    },
  });

  const lineageQuery = useQuery({
    queryKey: ["research-graph-lineage", selected?.artifact_id],
    enabled: selected != null,
    queryFn: async (): Promise<{ upstream: LineageNode[]; downstream: LineageNode[] }> => {
      const resp = await fetch(`/api/v1/artifacts/${selected!.artifact_id}/lineage`);
      if (!resp.ok) throw new Error("artifact.not_found");
      return resp.json();
    },
  });

  const nodes = graphQuery.data?.nodes ?? [];
  const groups = new Map<string, GraphNode[]>();
  for (const node of nodes) {
    const list = groups.get(node.artifact_type) ?? [];
    list.push(node);
    groups.set(node.artifact_type, list);
  }

  return (
    <main className="page" data-testid="research-graph-page">
      <h1>{t("nav.researchGraph")}</h1>
      <p className="secondary">{t("researchGraph.pageHint")}</p>
      {graphQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
      {graphQuery.data && nodes.length === 0 && (
        <p className="secondary">{t("researchGraph.empty")}</p>
      )}

      {nodes.length > 0 && (
        <div className="commander-grid">
          <aside className="commander-col commander-left" data-testid="graph-nodes">
            {[...groups.entries()].map(([type, list]) => (
              <section className="card" key={type}>
                <h3>
                  {formatArtifactType(type, lang)} · {list.length}
                </h3>
                <ul className="watch-list">
                  {list.map((node) => (
                    <li className="result-row" key={node.artifact_id}>
                      <button
                        type="button"
                        className={
                          selected?.artifact_id === node.artifact_id
                            ? "control-btn active"
                            : "control-btn"
                        }
                        onClick={() => setSelected(node)}
                      >
                        {node.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </aside>

          <section className="card" data-testid="graph-lineage">
            <h2>{t("researchGraph.lineageTitle")}</h2>
            {!selected && <p className="secondary">{t("researchGraph.selectHint")}</p>}
            {selected && (
              <>
                <div className="watch-card-head">
                  <h3 data-testid="lineage-selected">{selected.title}</h3>
                  <Link to={selected.route || "#"} className="control-btn">
                    {t("researchGraph.openArtifact")}
                  </Link>
                </div>
                {lineageQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
                {lineageQuery.data && (
                  <>
                    <p className="secondary">{t("researchGraph.upstream")}</p>
                    <ul className="result-list">
                      {lineageQuery.data.upstream.length === 0 ? (
                        <li className="secondary">{t("lineage.empty")}</li>
                      ) : (
                        lineageQuery.data.upstream.map((n) => (
                          <li className="result-row" key={n.artifact_id}>
                            <span className="secondary">{formatRelation(n.relation, lang)}</span>
                            <span>
                              {formatArtifactType(n.artifact_type, lang)} · {n.title}
                            </span>
                            <span className="secondary">{t("lineage.depth", { count: n.depth })}</span>
                          </li>
                        ))
                      )}
                    </ul>
                    <p className="secondary">{t("researchGraph.downstream")}</p>
                    <ul className="result-list">
                      {lineageQuery.data.downstream.length === 0 ? (
                        <li className="secondary">{t("lineage.empty")}</li>
                      ) : (
                        lineageQuery.data.downstream.map((n) => (
                          <li className="result-row" key={n.artifact_id}>
                            <span className="secondary">{formatRelation(n.relation, lang)}</span>
                            <span>
                              {formatArtifactType(n.artifact_type, lang)} · {n.title}
                            </span>
                            <span className="secondary">{t("lineage.depth", { count: n.depth })}</span>
                          </li>
                        ))
                      )}
                    </ul>
                  </>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
