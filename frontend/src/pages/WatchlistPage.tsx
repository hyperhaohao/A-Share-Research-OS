import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface WatchlistItem {
  instrument_id: string;
  note: string;
  added_at: string;
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

export function WatchlistPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [instrument, setInstrument] = useState("");

  const { data, isPending } = useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
  });

  const addMutation = useMutation({
    mutationFn: addWatchItem,
    onSuccess: () => {
      setInstrument("");
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
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
      {addMutation.isError && (
        <p className="status-error">
          {t(`errors.${addMutation.error.message}`, { defaultValue: t("common.error") })}
        </p>
      )}
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("watchlist.empty")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((item) => (
            <li key={item.instrument_id} className="result-row">
              <Link to={`/instrument/${item.instrument_id}`} className="result-code mono">
                {item.instrument_id}
              </Link>
              <span className="secondary">{item.note}</span>
              <button
                type="button"
                className="control-btn"
                aria-label={t("watchlist.remove")}
                onClick={() => removeMutation.mutate(item.instrument_id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
