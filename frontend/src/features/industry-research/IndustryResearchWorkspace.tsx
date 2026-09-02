import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Button } from "../../ui/guanlan";
import { ErrorState } from "../../ui/components";
import {
  fetchIndustryView,
  openWorkspaceWith,
  type IndustryView,
} from "./industryView";
import { IndustryChainView } from "./IndustryChainView";
import { GlobalIndustryPositionView } from "./GlobalIndustryPositionView";
import { IndustryGraphView } from "./IndustryGraphView";
import { IndustrySegmentDetail } from "./IndustrySegmentDetail";

type WorkspaceTab = "chain" | "global" | "graph";

/**
 * 产业研究三视图工作区（Guanlan Direct Port G2，方案 §7/§33）：
 * 产业链 + 全球产业坐标 + 环节详情一体（同一 IndustryView/IndustrySnapshot），
 * 不再是两个孤立页面。open_with_context 回工作台（Phase H 行为保留）。
 * /industry-map/:instrumentId 默认产业链 tab；/global-context/:instrumentId
 * 落全球坐标 tab —— 同一组件不同投影。
 */
export function IndustryResearchWorkspace({
  initialTab = "chain",
}: {
  initialTab?: WorkspaceTab;
}) {
  const pageTestid =
    initialTab === "global" ? "global-context-page" : "industry-map-page";
  const { t } = useTranslation();
  const { instrumentId } = useParams<{ instrumentId: string }>();
  const [tab, setTab] = useState<WorkspaceTab>(initialTab);
  const [segment, setSegment] = useState<string | null>(null);

  const viewQuery = useQuery({
    queryKey: ["industry-view", instrumentId],
    enabled: instrumentId != null,
    staleTime: 60_000,
    queryFn: () => fetchIndustryView(instrumentId!),
  });

  const backMutation = useMutation({
    mutationFn: async (view: IndustryView) => {
      if (view.map_id == null) throw new Error("artifact.not_found");
      return openWorkspaceWith(
        "industry_map",
        "IndustryMapSnapshot",
        view.map_id,
        view.instrument.instrument_id,
      );
    },
    onSuccess: (path: string) => {
      window.location.assign(path);
    },
  });

  if (viewQuery.isLoading) {
    return (
      <main className="page" data-testid={pageTestid}>
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (viewQuery.isError || !viewQuery.data || !instrumentId) {
    return (
      <main className="page" data-testid={pageTestid}>
        <h1>{t("industryWs.title")}</h1>
        <ErrorState
          message={t("industryWs.unavailable")}
          retry={() => void viewQuery.refetch()}
        />
        <LinkBack instrumentId={instrumentId} label={t("industryWs.backToWorkspace")} />
      </main>
    );
  }

  const view = viewQuery.data;

  return (
    <main className="page" data-testid={pageTestid}>
      <div className="ir-header">
        <div>
          <h1>{t("industryWs.title")}</h1>
          <p className="secondary">
            {view.industry_label ?? "—"}
            {view.instrument.name ? ` · ${view.instrument.name}` : ""}
            <span className="mono"> {view.instrument.code ?? ""}</span>
          </p>
        </div>
        <div className="ir-header-actions">
          <div className="ir-tabs" role="tablist" aria-label={t("industryWs.title")}>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "chain" && segment == null}
              className={`ir-tab${tab === "chain" && segment == null ? " ir-tab-on" : ""}`}
              onClick={() => {
                setTab("chain");
                setSegment(null);
              }}
            >
              {t("industryWs.tabChain")}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "global"}
              className={`ir-tab${tab === "global" ? " ir-tab-on" : ""}`}
              onClick={() => {
                setTab("global");
                setSegment(null);
              }}
            >
              {t("industryWs.tabGlobal")}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "graph"}
              className={`ir-tab${tab === "graph" ? " ir-tab-on" : ""}`}
              data-testid="ir-tab-graph"
              onClick={() => {
                setTab("graph");
                setSegment(null);
              }}
            >
              {t("industryWs.tabGraph")}
            </button>
          </div>
          <Button
            variant="primary"
            data-testid="industry-map-open-workspace"
            disabled={backMutation.isPending || view.map_id == null}
            onClick={() => backMutation.mutate(view)}
          >
            {t("industryWs.backToWorkspace")} →
          </Button>
        </div>
      </div>

      {tab === "chain" && segment != null && (
        <IndustrySegmentDetail
          instrumentId={instrumentId}
          segmentId={segment}
          onBack={() => setSegment(null)}
        />
      )}
      {tab === "chain" && segment == null && (
        <IndustryChainView view={view} onOpenSegment={(s) => setSegment(s)} />
      )}
      {tab === "global" && <GlobalIndustryPositionView view={view} />}
      {tab === "graph" && instrumentId != null && (
        <IndustryGraphView instrumentId={instrumentId} />
      )}

      <details className="technical-details gl-details">
        <summary className="secondary">{t("industryWs.technical")}</summary>
        <p className="secondary mono">
          map_id: {view.map_id ?? "—"} · context: {view.context_snapshot_id ?? "—"} · as_of:{" "}
          {view.as_of ?? "—"}
        </p>
        <ul className="secondary">
          {Object.entries(view.disclosures).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
          {Object.entries(view.global.disclosures).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
      </details>
    </main>
  );
}

function LinkBack({
  instrumentId,
  label,
}: {
  instrumentId: string | undefined;
  label: string;
}) {
  if (instrumentId == null) return null;
  return (
    <a className="control-btn" href={`/instrument/${encodeURIComponent(instrumentId)}`}>
      {label}
    </a>
  );
}
