import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Badge, Panel } from "../../ui/guanlan";
import type { IndustryView } from "./industryView";

/**
 * 产业链视图（donor 河图 → ASRO 真实链级，方案 §7/§8/§33）。
 * 阶段列（产业阶段分组）+ 环节 tile + 股票池（东财同业板块成员，真实）+
 * 驱动/传导/叙事面板：ASRO 尚无证据源 → 「暂无观点」显形（方案 §25，
 * donor 同款诚实约定），不画假边、不造假象限。
 */
export function IndustryChainView({
  view,
  onOpenSegment,
}: {
  view: IndustryView;
  onOpenSegment: (segmentId: string) => void;
}) {
  const { t } = useTranslation();
  const related = view.related_instruments;
  if (view.segments.length === 0) {
    return (
      <div className="ir-chain">
        <p className="status-error">{t("industryWs.chainMissing")}</p>
      </div>
    );
  }
  return (
    <div className="ir-chain">
      <div className="ir-chain-columns" data-testid="industry-chain">
        {view.segments.map((seg) => (
          <section
            key={seg.segment_id}
            className="ir-chain-col"
            data-col={seg.level}
          >
            <header className="ir-chain-col-head">
              <span className="ir-chain-level mono">{String(seg.level + 1).padStart(2, "0")}</span>
              <span className="ir-chain-col-name">{seg.name}</span>
              {seg.is_current && (
                <span className="ir-current-chip">{t("industryWs.currentIndustry")}</span>
              )}
            </header>
            <button
              type="button"
              className="ir-seg-tile"
              data-testid="industry-segment-tile"
              onClick={() => onOpenSegment(seg.segment_id)}
            >
              <span className="ir-seg-name">{seg.name}</span>
              <span className="ir-seg-meta mono">
                {seg.momentum == null ? "—" : `${seg.momentum > 0 ? "+" : ""}${seg.momentum}%`}
                {" · "}
                {seg.research_count == null
                  ? t("industryWs.researchNone")
                  : t("industryWs.researchCount", { count: seg.research_count })}
              </span>
              <span className="ir-seg-thermo" aria-hidden="true">
                <i style={{ width: `${seg.temperature ?? 0}%` }} />
              </span>
            </button>
          </section>
        ))}
      </div>

      <div className="ir-chain-side">
        <Panel title={t("industryWs.stockPool")} hint={view.disclosures.peers === "pending_relationship_source" ? t("industryWs.basisCooccur") : t("industryWs.basisBoard")}>
          {related.length === 0 ? (
            <p className="secondary" data-testid="industry-related-empty">
              {t("industryWs.noRelated")}
            </p>
          ) : (
            <ul className="watch-list" data-testid="industry-related">
              {related.map((r) => (
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

        <Panel title={t("industryWs.drivers")}>
          {view.semantics.drivers.length === 0 ? (
            <p className="secondary">{t("industryWs.pendingDrivers")}</p>
          ) : (
            <ul className="watch-list" data-testid="industry-drivers">
              {view.semantics.drivers.map((d) => (
                <li key={d.object_key} className="result-row ir-theme-row">
                  <span className="ir-theme-title">{d.title}</span>
                  {d.direction && (
                    <Badge
                      tone={
                        d.direction === "negative"
                          ? "down"
                          : d.direction === "positive"
                            ? "up"
                            : "neutral"
                      }
                    >
                      {t(`industryWs.direction.${d.direction}`)}
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={t("industryWs.transmission")}>
          {view.semantics.transmissions.length === 0 ? (
            <p className="secondary">{t("industryWs.pendingTransmission")}</p>
          ) : (
            <ul className="watch-list" data-testid="industry-transmissions">
              {view.semantics.transmissions.map((tr) => (
                <li key={tr.object_key} className="result-row ir-theme-row">
                  <span className="ir-theme-title">{tr.title}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={t("industryWs.narratives")}>
          {view.semantics.narratives.length === 0 ? (
            <p className="secondary">{t("industryWs.pendingNarratives")}</p>
          ) : (
            <ul className="watch-list" data-testid="industry-narratives">
              {view.semantics.narratives.map((nn) => (
                <li key={nn.object_key} className="result-row ir-theme-row">
                  <span className="ir-theme-title">{nn.title}</span>
                  {nn.status && <Badge tone="neutral">{t(`industryWs.nstatus.${nn.status}`)}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="ir-legend">
        <span>{t("industryWs.legendHint")}</span>
        <span className="secondary">{t("industryWs.legendEmpty")}</span>
      </div>
    </div>
  );
}
