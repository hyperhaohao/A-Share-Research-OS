import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import { fetchSegmentView } from "./industryView";

/**
 * 环节详情（donor 环节明细 → ASRO 真实数据，方案 §11）：
 * 环节定义/产业位置 + 相关上市公司（真实板块成员）+ 环节证据（真实共现检索）+
 * 最新研报 + 驱动/传导（暂无观点显形）。donor 缩放动效以轻量淡入保留。
 */
export function IndustrySegmentDetail({
  instrumentId,
  segmentId,
  onBack,
}: {
  instrumentId: string;
  segmentId: string;
  onBack: () => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const viewQuery = useQuery({
    queryKey: ["industry-segment", instrumentId, segmentId],
    queryFn: () => fetchSegmentView(instrumentId, segmentId),
  });

  if (viewQuery.isLoading) {
    return (
      <div className="ir-detail">
        <button type="button" className="gl-button" onClick={onBack}>
          ‹ {t("industryWs.backToChain")}
        </button>
        <p className="secondary">{t("common.loading")}</p>
      </div>
    );
  }
  if (viewQuery.isError || !viewQuery.data) {
    return (
      <div className="ir-detail">
        <button type="button" className="gl-button" onClick={onBack}>
          ‹ {t("industryWs.backToChain")}
        </button>
        <p className="status-error">{t("industryWs.segmentUnavailable")}</p>
      </div>
    );
  }

  const view = viewQuery.data;
  const seg = view.segment;
  const irBugT = (key: string) => t(`industryWs.${key}`);

  return (
    <div className="ir-detail" data-testid="industry-segment-detail">
      <div className="ir-detail-head">
        <button type="button" className="gl-button" onClick={onBack}>
          ‹ {t("industryWs.backToChain")}
        </button>
        <span className="ir-detail-seal seal">{seg?.name?.[0] ?? "·"}</span>
        <div>
          <div className="ir-detail-name">{seg?.name}</div>
          <div className="secondary mono">
            {view.industry_label}
            {seg?.is_current ? ` · ${irBugT("currentIndustry")}` : ""}
          </div>
        </div>
        <span className="secondary mono ir-detail-asof">
          {irBugT("asOf")}: {formatWhen(view.as_of, lang)}
        </span>
      </div>

      <div className="ir-detail-grid">
        <Panel title={irBugT("definition")}>
          {seg?.definition ? (
            <p>{seg.definition}</p>
          ) : (
            <p className="secondary">{irBugT("noDefinition")}</p>
          )}
        </Panel>

        <Panel title={irBugT("drivers")}>
          <p className="secondary">{irBugT("pendingDrivers")}</p>
        </Panel>

        <Panel title={irBugT("transmission")}>
          <p className="secondary">{irBugT("pendingTransmission")}</p>
        </Panel>

        <Panel title={irBugT("stockPool")}>
          {view.related_instruments.length === 0 ? (
            <p className="secondary">{irBugT("noRelated")}</p>
          ) : (
            <ul className="watch-list">
              {view.related_instruments.map((r) => (
                <li key={r.instrument_id} className="result-row">
                  <Link
                    to={`/instrument/${encodeURIComponent(r.instrument_id)}`}
                    className="result-name"
                  >
                    {r.name}
                  </Link>
                  <span className="secondary mono">{r.code}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={irBugT("segmentEvidence")} hint={`${seg?.evidence_count ?? 0}`}>
          {view.evidence.length === 0 ? (
            <p className="secondary">{irBugT("noEvidence")}</p>
          ) : (
            <ul className="watch-list" data-testid="segment-evidence">
              {view.evidence.map((e) => (
                <li key={e.evidence_id} className="result-row">
                  <span className="ir-theme-title">
                    {(e.summary || e.title).slice(0, 60) || "—"}
                    {(e.summary || e.title).length > 60 ? "…" : ""}
                  </span>
                  <span className="secondary mono">{formatWhen(e.available_time, lang)}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={irBugT("latestReports")}>
          {view.reports.length === 0 ? (
            <p className="secondary">{irBugT("noReports")}</p>
          ) : (
            <ul className="watch-list">
              {view.reports.map((r) => (
                <li key={r.report_id} className="result-row">
                  <Link to={`/reports/${r.report_id}`} className="result-name">
                    {r.name ?? r.code ?? irBugT("reportFallback")}
                  </Link>
                  <span className="secondary mono">{formatWhen(r.created_at, lang)}</span>
                  <Link to={`/reports/${r.report_id}`} className="control-btn">
                    {irBugT("openReport")}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
