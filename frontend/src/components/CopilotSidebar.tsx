/**
 * Research Copilot sidebar (整改 R4.2): asks the latest report of the
 * instrument via POST /reports/{id}/ask with copilot=true — LLM narrative
 * when configured, deterministic explain otherwise. Real API only.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface ReportRow {
  report_id: string;
  gate_status: string;
  language: string;
}

interface AskAnswer {
  mode: string;
  narrative_kind?: string;
  narrative?: string;
  claims: Array<{ claim_id: string; statement: string; evidence_ids: string[] }>;
  theses: Array<{ thesis_id: string; title: string }>;
  citations: string[];
  data_policy?: string;
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`http_${resp.status}`);
  return resp.json();
}

export function CopilotSidebar({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reportsQuery = useQuery({
    queryKey: ["copilot-reports", instrumentId],
    queryFn: () =>
      fetchJson<{ count: number; results: ReportRow[] }>(
        `/api/v1/reports?instrument_id=${encodeURIComponent(instrumentId)}`,
      ),
  });

  const latest = reportsQuery.data?.results[0];

  const ask = async () => {
    if (!latest || !question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/reports/${latest.report_id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), mode: "explain", copilot: true }),
      });
      if (!resp.ok) throw new Error(`http_${resp.status}`);
      setAnswer((await resp.json()) as AskAnswer);
      queryClient.invalidateQueries({ queryKey: ["copilot-asks"] });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="card copilot" data-testid="copilot-sidebar" aria-label={t("copilot.title")}>
      <h2>{t("copilot.title")}</h2>
      {!latest && <p className="secondary">{t("copilot.noReport")}</p>}
      {latest && (
        <>
          <div className="search-form">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
              placeholder={t("copilot.placeholder")}
              aria-label={t("copilot.title")}
            />
            <button type="button" className="control-btn" onClick={ask} disabled={busy}>
              →
            </button>
          </div>
          {error && <p className="status-error mono">{error}</p>}
          {busy && <p className="mono">{t("common.loading")}</p>}
          {answer && (
            <div data-testid="copilot-answer">
              <p className="mono secondary">
                {answer.narrative_kind === "llm"
                  ? t("copilot.llmNarrative")
                  : t("copilot.deterministic")}
              </p>
              {answer.narrative && <p>{answer.narrative}</p>}
              <p className="control-label">{t("copilot.claims")}</p>
              <ul>
                {answer.claims.map((c) => (
                  <li key={c.claim_id}>
                    {c.statement}
                    <span className="mono secondary"> [{c.evidence_ids.join(", ")}]</span>
                  </li>
                ))}
              </ul>
              <p className="mono secondary">
                {t("copilot.citations")}: {answer.citations.length}
              </p>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
