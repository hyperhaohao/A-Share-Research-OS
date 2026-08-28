import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { formatBoard, formatExchange, uiLang } from "../presentation/enumLabels";

interface InstrumentResult {
  matched_by: "code" | "name" | "alias";
  instrument: {
    instrument_id: string;
    code: string;
    name: string;
    exchange: string;
    board: string;
    market: string;
    industry: string | null;
  };
}

async function searchInstruments(query: string): Promise<{ count: number; results: InstrumentResult[] }> {
  const resp = await fetch(`/api/v1/instruments?query=${encodeURIComponent(query)}`);
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
  return resp.json();
}

/** Real API-driven instrument search; results show business identity (PW0). */
export function InstrumentSearch({ onSelect }: { onSelect?: (instrumentId: string) => void }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang = uiLang(i18n.language);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");

  const { data, isFetching, isError } = useQuery({
    queryKey: ["instruments", submitted],
    queryFn: () => searchInstruments(submitted),
    enabled: submitted.length > 0,
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(query.trim());
  };

  const open = (iid: string) => navigate(`/instrument/${encodeURIComponent(iid)}`);
  const runResearch = (iid: string) => {
    if (onSelect) onSelect(iid);
  };

  return (
    <section className="card" data-testid="instrument-search">
      <h2>{t("home.instrumentSearch")}</h2>
      <form onSubmit={onSubmit} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("home.searchPlaceholder")}
          aria-label={t("home.instrumentSearch")}
        />
        <button type="submit" className="control-btn" aria-label={t("home.instrumentSearch")}>
          →
        </button>
      </form>

      {submitted.length > 0 && (
        <div data-testid="search-results">
          {isError && <p className="status-error">{t("common.error")}</p>}
          {isFetching && !data && <p className="secondary">{t("common.loading")}</p>}
          {data && data.count === 0 && <p className="secondary">{t("home.searchEmpty")}</p>}
          {data &&
            data.results.map((r) => (
              <div key={r.instrument.instrument_id} className="result-row" style={{ cursor: "pointer" }}
                   onClick={() => open(r.instrument.instrument_id)}>
                <span className="result-name">{r.instrument.name}</span>
                <span className="mono result-code">{r.instrument.code}</span>
                <span className="secondary">
                  {formatExchange(r.instrument.exchange, lang)}
                  {r.instrument.board ? ` · ${formatBoard(r.instrument.board, lang)}` : ""}
                </span>
                <button type="button" className="control-btn"
                        onClick={(e) => { e.stopPropagation(); open(r.instrument.instrument_id); }}>
                  {t("workspace.open")}
                </button>
                {onSelect && (
                  <button type="button" className="control-btn"
                          onClick={(e) => { e.stopPropagation(); runResearch(r.instrument.instrument_id); }}>
                    {t("pipeline.run")}
                  </button>
                )}
              </div>
            ))}
        </div>
      )}
    </section>
  );
}
