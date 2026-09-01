import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Panel } from "../../ui/guanlan";
import { formatArtifactType, uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import { useInstrumentName } from "../../shared/instrument";
import type { Plan } from "./plan";
import {
  activateWorkbenchTab,
  closeWorkbenchTab,
  fetchWorkbenchTabs,
  resolveTabRoute,
} from "./workbench";

interface ArtifactLike {
  artifact_id: string;
  artifact_type: string;
  title: string;
  route: string;
}

interface RecentArtifact extends ArtifactLike {
  instrument_ids: string[];
  created_at: string | null;
}

interface PredictionItem {
  prediction_id: string;
  instrument_id: string;
  horizon: string;
  expected_direction: string;
  due_at: string;
  confidence?: number;
  consistency?: string;
  instrument?: { name: string | null; code: string } | null;
}

interface QuoteResponse {
  quote: {
    price: number;
    change_pct: number;
    pe_ttm: number | null;
    pb: number | null;
    total_market_cap_yuan: number | null;
  } | null;
  event_time: string | null;
}

/**
 * 右栏 = 真实当前 Workbench（方案 §6：不是固定 Artifact List）：
 * 当前标的速记卡（真实行情/估值）+ 当前计划产物（报告完成后置顶「打开报告」，
 * §32）+ 待验证预测。全部真实数据；缺失显形为 —（方案 §25）。
 */
export function CommandCenterWorkbench({
  activePlan,
  selectedInstrument,
  pendingPredictions,
  sessionId,
}: {
  activePlan: Plan | null;
  selectedInstrument: string | null;
  pendingPredictions: PredictionItem[];
  sessionId: string | null;
}) {
  const { t } = useTranslation();
  const instrumentId = activePlan?.instrument_id ?? selectedInstrument ?? null;
  return (
    <>
      {sessionId != null && <WorkbenchTabs sessionId={sessionId} />}

      {instrumentId ? (
        <InstrumentBriefCard instrumentId={instrumentId} activePlan={activePlan} />
      ) : (
        <Panel title={t("commander.artifacts")}>
          <div className="cc-empty-hint">
            <p className="cc-empty-title">{t("cc.workbenchEmptyTitle")}</p>
            <p className="secondary">{t("cc.workbenchEmptyHint")}</p>
          </div>
        </Panel>
      )}

      <ArtifactsSection activePlan={activePlan} hasInstrument={instrumentId != null} />

      <Panel title={t("commandCenter.pendingPredictions")}>
        {pendingPredictions.length === 0 ? (
          <p className="secondary">{t("commandCenter.noPredictions")}</p>
        ) : (
          <ul className="watch-list">
            {pendingPredictions.map((p) => (
              <PredRow key={p.prediction_id} prediction={p} />
            ))}
          </ul>
        )}
        <p>
          <Link to="/predictions" className="secondary">
            {t("commandCenter.goPredictions")} →
          </Link>
        </p>
      </Panel>
    </>
  );
}

/** 当前标的速记卡（donor RightRail「当前标的 · 速记」→ ASRO 真实行情）。 */
function InstrumentBriefCard({
  instrumentId,
  activePlan,
}: {
  instrumentId: string;
  activePlan: Plan | null;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(instrumentId);

  const quoteQuery = useQuery({
    queryKey: ["cc-quote", instrumentId],
    enabled: instrumentId != null,
    staleTime: 15000,
    refetchInterval: 30000,
    queryFn: async (): Promise<QuoteResponse | null> => {
      const resp = await fetch(
        "/api/v1/market-data/quote?instrument=" + encodeURIComponent(instrumentId),
      );
      if (!resp.ok) return null;
      return (await resp.json()) as QuoteResponse;
    },
  });

  const quote = quoteQuery.data?.quote ?? null;
  const up = (quote?.change_pct ?? 0) >= 0;
  const cap = quote?.total_market_cap_yuan;
  const capText = cap == null ? "—" : (cap / 1e8).toFixed(0); // 亿元

  const hasPlanArtifacts =
    (activePlan?.steps ?? []).flatMap((s) => s.artifact_ids).length > 0;

  return (
    <Panel title={t("cc.briefCard")}>
      <div className="cc-brief-card" data-testid="commander-brief-card">
        <div className="cc-brief-head">
          <div>
            <div className="cc-brief-name">{profile?.name ?? instrumentId}</div>
            <div className="secondary mono cc-brief-code">{profile?.code ?? ""}</div>
          </div>
          {quote ? (
            <div className="cc-brief-quote">
              <div className={"num " + (up ? "up" : "down") + " cc-brief-price"}>
                {quote.price.toFixed(2)}
              </div>
              <div className={"num " + (up ? "up" : "down") + " cc-brief-delta"}>
                {up ? "+" : ""}
                {quote.change_pct.toFixed(2)}%
              </div>
            </div>
          ) : (
            <div className="secondary">{t("cc.quoteUnavailable")}</div>
          )}
        </div>

        {quote && (
          <div className="cc-brief-grid">
            <div className="cc-brief-cell">
              <div className="cc-brief-label">PE(TTM)</div>
              <div className="num">
                {quote.pe_ttm == null ? "—" : quote.pe_ttm.toFixed(1)}
              </div>
            </div>
            <div className="cc-brief-cell">
              <div className="cc-brief-label">PB</div>
              <div className="num">
                {quote.pb == null ? "—" : quote.pb.toFixed(2)}
              </div>
            </div>
            <div className="cc-brief-cell">
              <div className="cc-brief-label">{t("cc.marketCap")}</div>
              <div className="num">
                {capText}
                <span className="cc-brief-unit">{t("cc.yi")}</span>
              </div>
            </div>
          </div>
        )}

        <div className="cc-brief-foot">
          {hasPlanArtifacts && activePlan ? (
            <Link to={"/reports"} className="cc-brief-report">
              {t("cc.openCurrentReport")} <span className="cc-brief-arrow">→</span>
            </Link>
          ) : (
            <span className="secondary mono cc-brief-hint">
              {t("cc.briefHintNoReport")}
            </span>
          )}
          <Link to={"/instrument/" + instrumentId} className="secondary cc-brief-ws">
            {t("cc.openWorkspace")} →
          </Link>
        </div>

        {quoteQuery.data?.event_time && (
          <p className="secondary mono cc-brief-time">
            {t("cc.quoteAsOf")}: {formatWhen(quoteQuery.data.event_time, lang)}
          </p>
        )}
      </div>
    </Panel>
  );
}

/** 当前研究产物（真实当前 Workbench：优先当前计划 Artifact，否则最近产物）。 */
function ArtifactsSection({
  activePlan,
  hasInstrument,
}: {
  activePlan: Plan | null;
  hasInstrument: boolean;
}) {
  const { t } = useTranslation();

  const planArtifactIds = (activePlan?.steps ?? [])
    .flatMap((s) => s.artifact_ids)
    .filter((id) => id.startsWith("art_"));

  const planArtifacts = useQuery({
    queryKey: ["plan-artifacts", planArtifactIds.join(",")],
    enabled: planArtifactIds.length > 0,
    staleTime: 10000,
    queryFn: async (): Promise<ArtifactLike[]> => {
      const results = await Promise.all(
        planArtifactIds.map(async (id) => {
          const resp = await fetch("/api/v1/artifacts/" + id);
          if (!resp.ok) return null;
          const body = (await resp.json()) as { artifact: ArtifactLike };
          return body.artifact;
        }),
      );
      return results.filter((a): a is ArtifactLike => a != null);
    },
  });

  const recent = useQuery({
    queryKey: ["recent-artifacts"],
    enabled: planArtifactIds.length === 0,
    refetchInterval: 15000,
    queryFn: async (): Promise<RecentArtifact[]> => {
      const resp = await fetch("/api/v1/artifacts?limit=8");
      if (!resp.ok) return [];
      const body = (await resp.json()) as { results: RecentArtifact[] };
      return body.results;
    },
  });

  const artifacts: ArtifactLike[] =
    planArtifactIds.length > 0 ? (planArtifacts.data ?? []) : (recent.data ?? []);

  return (
    <Panel title={t("commander.artifacts")}>
      <div data-testid="commander-artifacts">
        {artifacts.length === 0 ? (
          <p className="secondary">{t("commander.noArtifacts")}</p>
        ) : (
          <ul className="watch-list">
            {artifacts.map((a) => (
              <ArtifactRow key={a.artifact_id} artifact={a} />
            ))}
          </ul>
        )}
      </div>
      {hasInstrument && (
        <p className="secondary artifacts-hint">{t("commander.artifactsHint")}</p>
      )}
    </Panel>
  );
}

function ArtifactRow({ artifact }: { artifact: ArtifactLike }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const isReport = artifact.artifact_type === "report";
  return (
    <li className="result-row" data-testid="artifact-row">
      <Link to={artifact.route || "#"} className="result-name">
        {artifact.title}
      </Link>
      <span className="secondary">{formatArtifactType(artifact.artifact_type, lang)}</span>
      {isReport && (
        <Link to={artifact.route || "#"} className="control-btn" data-testid="artifact-open">
          {t("commander.openReport")}
        </Link>
      )}
    </li>
  );
}

function PredRow({ prediction: p }: { prediction: PredictionItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(p.instrument_id);
  return (
    <li className="result-row">
      <Link to={"/instrument/" + p.instrument_id}>
        {profile?.name ?? p.instrument_id}
      </Link>
      <span className="secondary">{t("workspace.direction." + p.expected_direction)}</span>
      <span className="secondary">
        {t("predictions.dueBy", { date: formatWhen(p.due_at, lang) })}
      </span>
    </li>
  );
}

/**
 * F8 动态 Workbench（任务书 §8.7）：右栏不再是固定信息卡 ——
 * Artifact/Tool Result 自动打开注册表页面 Tab（后端 open_for_artifacts），
 * 每会话独立状态（服务端持久化 → 刷新恢复）；Tab payload 驱动真实页面
 * （route 占位符 + artifact 溯源参数）+「在完整页面打开」不丢上下文。
 */
function WorkbenchTabs({ sessionId }: { sessionId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const tabsQuery = useQuery({
    queryKey: ["cc-workbench-tabs", sessionId],
    enabled: sessionId != null,
    refetchInterval: 5000,
    queryFn: () => fetchWorkbenchTabs(sessionId),
  });
  const tabs = tabsQuery.data ?? [];
  const active = tabs.find((tab) => tab.is_active) ?? null;

  return (
    <Panel title={t("cc.workbenchTabs")}>
      <div data-testid="workbench-tabs">
      {tabs.length === 0 ? (
        <p className="secondary">{t("cc.workbenchEmpty")}</p>
      ) : (
        <>
          <div className="cc-wb-strip" data-testid="workbench-tab-strip">
            {tabs.map((tab) => (
              <button
                key={tab.tab_id}
                className={"cc-wb-tab" + (tab.is_active ? " cc-wb-tab-active" : "")}
                data-testid={"workbench-tab-" + tab.page}
                onClick={() => {
                  void activateWorkbenchTab(sessionId, tab.tab_id).then(() => {
                    void queryClient.invalidateQueries({
                      queryKey: ["cc-workbench-tabs", sessionId],
                    });
                  });
                }}
              >
                <span className="cc-wb-tab-title">{tab.title}</span>
                <span
                  className="cc-wb-tab-close"
                  data-testid={"workbench-close-" + tab.tab_id}
                  onClick={(event) => {
                    event.stopPropagation();
                    void closeWorkbenchTab(sessionId, tab.tab_id).then(() => {
                      void queryClient.invalidateQueries({
                        queryKey: ["cc-workbench-tabs", sessionId],
                      });
                    });
                  }}
                >
                  ×
                </span>
              </button>
            ))}
          </div>

          {active && (
            <div className="cc-wb-body" data-testid="workbench-tab-active">
              <div className="cc-wb-body-head">
                <span className="cc-wb-page mono">{active.page}</span>
                <span className="cc-wb-title">{active.title}</span>
              </div>
              {active.payload?.instrument_ids != null &&
                Array.isArray(active.payload.instrument_ids) &&
                active.payload.instrument_ids.length > 0 && (
                  <p className="secondary mono cc-wb-meta">
                    {active.payload.instrument_ids.join(" · ")}
                  </p>
                )}
              <Link to={resolveTabRoute(active)} className="control-btn cc-wb-open">
                {t("cc.workbenchOpenFull")}
              </Link>
            </div>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}
