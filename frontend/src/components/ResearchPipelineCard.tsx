import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface PipelineEvent {
  event: string;
  run_id?: string;
  [key: string]: unknown;
}

async function runPipeline(runId: string, signal: AbortSignal): Promise<{ events: PipelineEvent[]; report_id: string }> {
  const resp = await fetch(`/api/v1/pipeline/run?instrument=600519&run_id=${encodeURIComponent(runId)}`, {
    method: "POST",
    signal,
  });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
  return resp.json();
}

/**
 * Real SSE hookup: subscribe to /events/stream for a client-generated run id,
 * trigger the pipeline, render events as they stream, close on completion.
 */
export function ResearchPipelineCard() {
  const { t } = useTranslation();
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (runId: string) => runPipeline(runId, new AbortController().signal),
  });

  const start = () => {
    setEvents([]);
    setError(null);
    setRunning(true);
    const runId = `run_${crypto.randomUUID().slice(0, 12)}`;

    const source = new EventSource(`/api/v1/events/stream?run_id=${encodeURIComponent(runId)}`);
    source.addEventListener("run_completed", () => source.close());
    source.addEventListener("run_failed", () => source.close());
    source.onerror = () => {
      /* keep the UI alive; pipeline result arrives via mutation */
    };
    source.onmessage = () => undefined;

    const names: string[] = [];
    const capture = (e: MessageEvent) => {
      names.push(e.type);
    };
    const eventNames = [
      "run_started", "source_progress", "evidence_ready", "quality_gate",
      "analyst_progress", "valuation_ready", "report_ready", "run_completed", "run_failed",
    ];
    for (const name of eventNames) {
      source.addEventListener(name, capture as EventListener);
    }

    mutation.mutate(runId, {
      onSuccess: (data) => {
        setEvents(data.events);
        setRunning(false);
        source.close();
      },
      onError: (err: Error) => {
        setError(err.message);
        setRunning(false);
        source.close();
      },
    });
    void names;
  };

  return (
    <section className="card" data-testid="pipeline-card">
      <h2>{t("pipeline.title")}</h2>
      <button type="button" className="control-btn" onClick={start} disabled={running}>
        {t("pipeline.run")}
      </button>
      {error && (
        <p className="status-error mono">
          {t(`errors.${error}`, { defaultValue: t("common.error") })}
        </p>
      )}
      {events.length > 0 && (
        <ol className="pipeline-events" data-testid="pipeline-events">
          {events.map((e, i) => (
            <li key={i} className="mono">
              <span className={e.event === "run_failed" ? "status-error" : "status-ok"}>
                {e.event}
              </span>
              {e.report_id ? ` · ${String(e.report_id)}` : ""}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
