import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatBoard, formatExchange, uiLang } from "../presentation/enumLabels";
import { formatPct, formatWhen } from "../presentation/format";
import { contextPath, newResearchContext } from "../shared/context";

/**
 * 关注池（UX Foundation）：页面只消费 /views/watchlist 聚合视图 ——
 * 身份/行情/研究状态/报告/预测/盯盘由后端 Read Model 一次装配，
 * 前端不再逐卡串多个 API 自行拼装（评审 §四）。
 */

interface WatchCardView {
  instrument_id: string;
  instrument: {
    instrument_id: string;
    name: string | null;
    code: string;
    exchange: string;
    board: string;
  } | null;
  quote: { price: number; change_pct: number | null; quote_time: string | null } | null;
  research: { judgment: string | null; confidence: number | null; thesis_title: string | null };
  report: { report_id: string; created_at: string | null } | null;
  prediction: {
    prediction_id: string;
    horizon: string;
    expected_direction: string;
    expected_return_range: [number, number];
    validated: boolean;
    due_at: string | null;
  } | null;
  monitor: { monitor_id: string; enabled: boolean; next_run_at: string | null } | null;
  added_at: string | null;
}

const JUDGMENT_KEY: Record<string, string> = {
  up: "workspace.direction.up",
  down: "workspace.direction.down",
  neutral: "workspace.direction.neutral",
};

function WatchCard({
  view,
  onRemove,
}: {
  view: WatchCardView;
  onRemove: (id: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const instrumentId = view.instrument_id;
  const ctx = newResearchContext({
    primary_instrument_id: instrumentId,
    instrument_ids: [instrumentId],
  });
  const inst = view.instrument;

  return (
    <li className="card watch-card" data-testid="watch-card">
      <div className="watch-card-head">
        <Link to={`/instrument/${instrumentId}`} className="watch-card-name">
          {inst?.name ?? inst?.code ?? instrumentId}
        </Link>
        {inst && (
          <span className="secondary">
            {inst.code} · {formatExchange(inst.exchange, lang)}
            {inst.board ? ` · ${formatBoard(inst.board, lang)}` : ""}
          </span>
        )}
      </div>

      <div className="watch-card-quote mono">
        {view.quote ? (
          <>
            <span>{view.quote.price}</span>
            <span className={(view.quote.change_pct ?? 0) >= 0 ? "pct-up" : "pct-down"}>
              {formatPct(view.quote.change_pct ?? undefined)}
            </span>
          </>
        ) : (
          <span className="secondary">{t("label.no_data")}</span>
        )}
      </div>

      <div className="watch-card-state">
        <span>
          {view.research.judgment
            ? `${t("watchlist.researchState")}: ${t(JUDGMENT_KEY[view.research.judgment])}`
            : t("watchlist.noResearch")}
        </span>
        {view.report && (
          <span className="secondary">
            {t("watchlist.lastResearch")}: {formatWhen(view.report.created_at, lang)}
          </span>
        )}
        {view.prediction && (
          <span className="secondary">
            {t("watchlist.predictionShort", {
              horizon: view.prediction.horizon,
              direction: t(JUDGMENT_KEY[view.prediction.expected_direction] ?? ""),
            })}
            {" · "}
            {view.prediction.validated ? t("predictions.validated") : t("predictions.pending")}
          </span>
        )}
        {view.monitor && (
          <span className="secondary">
            {t("watchlist.monitorOn")}
            {view.monitor.next_run_at ? ` · ${formatWhen(view.monitor.next_run_at, lang)}` : ""}
          </span>
        )}
      </div>

      <div className="header-controls">
        <Link className="control-btn" to={contextPath(`/instrument/${instrumentId}`, ctx)}>
          {t("workspace.open")}
        </Link>
        <Link className="control-btn" to={contextPath("/", ctx, { run: true })}>
          {t("watchlist.researchNow")}
        </Link>
        {view.report && (
          <Link className="control-btn" to={contextPath(`/reports/${view.report.report_id}`, ctx)}>
            {t("watchlist.viewReport")}
          </Link>
        )}
        <Link className="control-btn" to={contextPath("/tasks", ctx)}>
          {t("watchlist.continuous")}
        </Link>
        <button
          type="button"
          className="control-btn"
          aria-label={t("watchlist.remove")}
          onClick={() => onRemove(instrumentId)}
        >
          ×
        </button>
      </div>
    </li>
  );
}

async function addWatchItem(instrument: string): Promise<void> {
  const resp = await fetch("/api/v1/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instrument }),
  });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
}

async function removeWatchItem(instrumentId: string): Promise<void> {
  const resp = await fetch(`/api/v1/watchlist/${encodeURIComponent(instrumentId)}`, {
    method: "DELETE",
  });
  if (!resp.ok && resp.status !== 204) throw new Error("network.unreachable");
}

export function WatchlistPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [instrument, setInstrument] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  // 单请求消费 Read Model（评审 §十二：页面不再串多个 API 自行拼装）
  const { data, isPending, isError } = useQuery({
    queryKey: ["watchlist-view"],
    queryFn: async (): Promise<WatchCardView[]> => {
      const resp = await fetch("/api/v1/views/watchlist");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { results: WatchCardView[] };
      return body.results;
    },
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["watchlist-view"] });
    queryClient.invalidateQueries({ queryKey: ["watchlist"] });
  };

  const addMutation = useMutation({
    mutationFn: addWatchItem,
    onSuccess: () => {
      setInstrument("");
      setAddError(null);
      invalidate();
    },
    onError: (err: Error) => setAddError(err.message),
  });
  const removeMutation = useMutation({
    mutationFn: removeWatchItem,
    onSuccess: invalidate,
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (instrument.trim()) addMutation.mutate(instrument.trim());
  };

  return (
    <main className="page" data-testid="watchlist-page">
      <h1>{t("nav.watchlist")}</h1>
      <form onSubmit={onSubmit} className="search-form">
        <input
          type="text"
          value={instrument}
          onChange={(e) => setInstrument(e.target.value)}
          placeholder={t("home.searchPlaceholder")}
          aria-label={t("nav.watchlist")}
        />
        <button type="submit" className="control-btn" aria-label={t("watchlist.add")}>
          +
        </button>
      </form>
      {addError && (
        <p className="status-error">
          {t(`errors.${addError}`, { defaultValue: t("common.error") })}
        </p>
      )}
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("watchlist.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list watch-cards">
          {data.map((view) => (
            <WatchCard
              key={view.instrument_id}
              view={view}
              onRemove={(id) => removeMutation.mutate(id)}
            />
          ))}
        </ul>
      )}
    </main>
  );
}
