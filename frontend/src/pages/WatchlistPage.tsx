import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { formatBoard, formatExchange, uiLang } from "../presentation/enumLabels";
import { formatPct, formatWhen } from "../presentation/format";

interface WatchlistItem {
  instrument_id: string;
  note: string;
  added_at: string;
}

interface Quote {
  quote?: { price?: number | null; change_pct?: number | null; name?: string | null };
}

interface ReportSummary {
  report_id: string;
  created_at: string | null;
  latest_version_no: number;
  gate_status: string;
}

async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const resp = await fetch("/api/v1/watchlist");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
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

/** One watchlist entry: identity + quote + research state + actions (PW2). */
function WatchCard({ instrumentId, onRemove }: { instrumentId: string; onRemove: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);

  const profileQuery = useQuery({
    queryKey: ["instrument", instrumentId],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(instrumentId)}`);
      if (!resp.ok) throw new Error("instrument.not_found");
      const body = await resp.json();
      return body.instrument as {
        code: string;
        name: string;
        exchange: string;
        board: string;
        industry: string | null;
      };
    },
  });

  const quoteQuery = useQuery({
    queryKey: ["quote", instrumentId],
    queryFn: async (): Promise<Quote> => {
      const resp = await fetch(`/api/v1/market-data/quote?instrument=${encodeURIComponent(instrumentId)}`);
      if (!resp.ok) return {};
      return resp.json();
    },
    staleTime: 5000,
  });

  const reportQuery = useQuery({
    queryKey: ["reports", instrumentId],
    queryFn: async (): Promise<ReportSummary | null> => {
      const resp = await fetch(`/api/v1/reports?instrument_id=${encodeURIComponent(instrumentId)}`);
      if (!resp.ok) return null;
      const body = await resp.json();
      return (body.results?.[0] as ReportSummary) ?? null;
    },
  });

  const profile = profileQuery.data;
  const quote = quoteQuery.data?.quote;
  const report = reportQuery.data;

  return (
    <li className="card watch-card" data-testid="watch-card">
      <div className="watch-card-head">
        <Link to={`/instrument/${instrumentId}`} className="watch-card-name">
          {profile?.name ?? instrumentId}
        </Link>
        {profile && (
          <span className="secondary">
            {profile.code} · {formatExchange(profile.exchange, lang)}
            {profile.board ? ` · ${formatBoard(profile.board, lang)}` : ""}
          </span>
        )}
      </div>

      <div className="watch-card-quote mono">
        {quote?.price != null ? (
          <>
            <span>{quote.price}</span>
            <span className={(quote.change_pct ?? 0) >= 0 ? "pct-up" : "pct-down"}>
              {formatPct(quote.change_pct ?? undefined)}
            </span>
          </>
        ) : (
          <span className="secondary">{t("label.no_data")}</span>
        )}
      </div>

      <div className="watch-card-state">
        {report ? (
          <>
            <span>
              {t("watchlist.lastResearch")}: {formatWhen(report.created_at, lang)}
            </span>
            <span className="secondary">
              {t("watchlist.hasReport", { version: report.latest_version_no })}
            </span>
          </>
        ) : (
          <span className="secondary">{t("watchlist.noResearch")}</span>
        )}
      </div>

      <div className="header-controls">
        <Link className="control-btn" to={`/instrument/${instrumentId}`}>
          {t("workspace.open")}
        </Link>
        <Link className="control-btn" to={`/?instrument=${encodeURIComponent(instrumentId)}&run=1`}>
          {t("watchlist.researchNow")}
        </Link>
        {report && (
          <Link className="control-btn" to={`/reports/${report.report_id}`}>
            {t("watchlist.viewReport")}
          </Link>
        )}
        <Link className="control-btn" to={`/tasks?instrument=${encodeURIComponent(instrumentId)}`}>
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

export function WatchlistPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [instrument, setInstrument] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const { data, isPending } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });

  const addMutation = useMutation({
    mutationFn: addWatchItem,
    onSuccess: () => {
      setInstrument("");
      setAddError(null);
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
    onError: (err: Error) => setAddError(err.message),
  });
  const removeMutation = useMutation({
    mutationFn: removeWatchItem,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
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
      {data && data.length === 0 && <p className="secondary">{t("watchlist.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list watch-cards">
          {data.map((item) => (
            <WatchCard
              key={item.instrument_id}
              instrumentId={item.instrument_id}
              onRemove={(id) => removeMutation.mutate(id)}
            />
          ))}
        </ul>
      )}
    </main>
  );
}
