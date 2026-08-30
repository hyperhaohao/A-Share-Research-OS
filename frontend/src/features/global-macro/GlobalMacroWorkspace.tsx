import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { MetricCell, Panel } from "../../ui/guanlan";
import { ErrorState } from "../../ui/components";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen as formatWhenTime } from "../../presentation/format";

/**
 * 全球宏观工作台（Guanlan Direct Port G8，方案 §12/§13/§39）：
 * 回答「当前整个资本市场处于怎样的全球宏观环境」—— 与产业研究·全球产业坐标
 * 分离（§12）。市场状态按区域归组（中国/香港/美国/商品）+ 宏观主题 +
 * 风险偏好（donor 温度计依赖预测市场源，ASRO 无 → 显形暂无，§25）。
 * 数据全部来自 ASRO GlobalContextSnapshot（真实行情数值层 + 宏观证据主题）。
 */

interface MacroIndicator {
  code: string;
  name: string;
  value: number | null;
  change: number | null;
  market_time: string;
  available_time: string;
}

interface MacroTheme {
  title: string;
  topic: string | null;
  mentions_official_body: boolean;
  summary: string;
  available_time: string;
  evidence_id: string;
}

interface GlobalMacroView {
  indicators: MacroIndicator[];
  themes: MacroTheme[];
  disclosures: Record<string, string>;
  as_of: string | null;
  has_data: boolean;
}

const REGION_PREFIXES: Array<{ regionKey: string; match: (code: string) => boolean }> = [
  { regionKey: "china", match: (c) => c.startsWith("sh") || c.startsWith("sz") },
  { regionKey: "hongkong", match: (c) => c.startsWith("hk") },
  { regionKey: "us", match: (c) => c.startsWith("us") },
  { regionKey: "commodity", match: (c) => c.startsWith("hf") },
];

export function GlobalMacroWorkspace() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const viewQuery = useQuery({
    queryKey: ["global-macro"],
    refetchInterval: 60_000,
    queryFn: async (): Promise<GlobalMacroView> => {
      const resp = await fetch("/api/v1/views/global-macro");
      if (!resp.ok) throw new Error("network.unreachable");
      return (await resp.json()).view;
    },
  });

  return (
    <main className="page" data-testid="global-macro-page">
      <div className="watch-card-head">
        <h1 className="serif">{t("macroWs.title")}</h1>
        <span className="secondary">{t("macroWs.subtitle")}</span>
      </div>
      <p className="secondary">
        {viewQuery.data?.as_of
          ? `${t("macroWs.asOf")}: ${formatWhenTime(viewQuery.data.as_of, lang)}`
          : ""}
      </p>

      {viewQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
      {viewQuery.isError && (
        <ErrorState message={t("macroWs.unavailable")} retry={() => void viewQuery.refetch()} />
      )}

      {viewQuery.data && (
        <>
          {!viewQuery.data.has_data && (
            <p className="secondary" data-testid="global-macro-empty">
              {viewQuery.data.disclosures.note ?? t("macroWs.empty")}
            </p>
          )}

          <div className="gm-regions">
            {REGION_PREFIXES.map(({ regionKey, match }) => {
              const inds = viewQuery.data!.indicators.filter((i) => match(i.code));
              return (
                <Panel key={regionKey} title={t(`macroWs.region.${regionKey}`)}>
                  {inds.length === 0 ? (
                    <p className="secondary">—</p>
                  ) : (
                    <div className="gm-region-row">
                      {inds.map((ind) => (
                        <MetricCell
                          key={ind.code}
                          label={ind.name}
                          value={ind.value == null ? "—" : ind.value.toLocaleString()}
                          delta={
                            ind.change == null
                              ? undefined
                              : `${ind.change > 0 ? "+" : ""}${ind.change.toFixed(2)}%`
                          }
                        />
                      ))}
                    </div>
                  )}
                </Panel>
              );
            })}
          </div>

          <div className="gm-lower">
            <Panel title={t("macroWs.themesTitle")} hint={t("macroWs.themesHint")}>
              {viewQuery.data.themes.length === 0 ? (
                <p className="secondary">{t("macroWs.noThemes")}</p>
              ) : (
                <ul className="watch-list" data-testid="global-macro-themes">
                  {viewQuery.data.themes.map((th) => (
                    <li key={th.evidence_id} className="result-row">
                      <span className="ir-theme-title">
                        {th.summary.slice(0, 70)}
                        {th.summary.length > 70 ? "…" : ""}
                      </span>
                      <span className="secondary mono">
                        {formatWhenTime(th.available_time, lang)}
                        {th.mentions_official_body ? ` · ${t("macroWs.officialMention")}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title={t("macroWs.riskTitle")} hint={t("macroWs.riskHint")}>
              <p className="secondary" data-testid="global-macro-risk-pending">
                {t("macroWs.riskPending")}
              </p>
            </Panel>
          </div>

          <details className="technical-details gl-details">
            <summary className="secondary">{t("macroWs.technical")}</summary>
            <p className="secondary mono">
              {viewQuery.data.disclosures.note ?? "—"}
            </p>
          </details>
        </>
      )}
    </main>
  );
}
