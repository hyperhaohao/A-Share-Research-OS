import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  formatAnalyst,
  formatCapability,
} from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

interface PipelineEvent {
  event: string;
  run_id?: string;
  at?: string;
  capability?: string;
  status?: string;
  created?: number;
  analyst?: string;
  gate?: string;
  blocked?: boolean;
  report_id?: string;
  thesis_id?: string;
  evidence_count?: number;
  count?: number;
  scenarios?: number;
  risks?: number;
  supporting?: number;
  opposing?: number;
  methods?: string[];
  error?: string;
  [key: string]: unknown;
}

interface PipelineResult {
  run_id: string;
  report_id: string;
  gate_status: string;
  thesis_id?: string;
  claim_count?: number;
  valuation_count?: number;
  events: PipelineEvent[];
}

/** All named SSE events the backend bus publishes (任务书 §67 + pipeline). */
const SSE_EVENT_NAMES = [
  "run_started",
  "source_progress",
  "evidence_ready",
  "snapshot_built",
  "quality_gate",
  "analyst_progress",
  "claims_compiled",
  "thesis_ready",
  "debate_ready",
  "valuation_ready",
  "scenario_ready",
  "risk_ready",
  "report_ready",
  "run_completed",
  "run_failed",
  // R4 自主研究循环语义事件（方案 §10.3/§10.4/§10.5）
  "profile_applied",
  "waiting_data",
  "reviewing",
  "missing_data_summary",
];

type Lang = "zh" | "en";

interface StageLine {
  key: string;
  icon: "done" | "warn" | "missing" | "wait" | "fail";
  label: string;
  detail?: string;
}

interface Stage {
  key: string;
  title: string;
  progress?: string;
  lines: StageLine[];
}

function iconChar(icon: StageLine["icon"]): string {
  switch (icon) {
    case "done":
      return "✓";
    case "warn":
      return "⚠";
    case "missing":
      return "○";
    case "fail":
      return "✕";
    default:
      return "…";
  }
}

/** Collection stage: merge source_progress + evidence_ready per capability. */
function collectStage(events: PipelineEvent[], lang: Lang): Stage | null {
  const order: string[] = [];
  const byCap = new Map<
    string,
    { status: string; created: number | undefined; done: boolean }
  >();
  for (const e of events) {
    if (e.event === "source_progress" && e.capability) {
      if (!byCap.has(e.capability)) order.push(e.capability);
      byCap.set(e.capability, { status: "fetching", created: undefined, done: false });
    } else if (e.event === "evidence_ready" && e.capability) {
      if (!byCap.has(e.capability)) order.push(e.capability);
      byCap.set(e.capability, {
        status: e.status ?? "unknown",
        created: e.created,
        done: true,
      });
    }
  }
  if (order.length === 0) return null;
  const lines: StageLine[] = order.map((cap) => {
    const info = byCap.get(cap)!;
    const ok = info.done && (info.status === "success" || info.status === "partial");
    const missing = info.done && info.status === "no_data";
    const failed = info.done && !ok && !missing;
    return {
      key: `cap-${cap}`,
      icon: ok ? "done" : missing ? "missing" : failed ? "warn" : "wait",
      label: formatCapability(cap, lang),
      detail: !info.done
        ? lang === "zh"
          ? "采集中"
          : "collecting"
        : (info.created ?? 0) > 0
          ? `${info.created} ${lang === "zh" ? "条新证据" : "new items"}`
          : lang === "zh"
            ? "已收录"
            : "covered",
    };
  });
  const done = order.filter((c) => byCap.get(c)!.done).length;
  return { key: "collect", title: lang === "zh" ? "数据采集" : "Data collection", progress: `${done}/${order.length}`, lines };
}

/** Analysis stage: merge analyst_progress per analyst (latest status wins). */
function analysisStage(events: PipelineEvent[], lang: Lang): Stage | null {
  const order: string[] = [];
  const byAnalyst = new Map<string, string>();
  for (const e of events) {
    if (e.event === "analyst_progress" && e.analyst) {
      if (!byAnalyst.has(e.analyst)) order.push(e.analyst);
      byAnalyst.set(e.analyst, e.status ?? "ok");
    }
  }
  if (order.length === 0) return null;
  const lines: StageLine[] = order.map((a) => {
    const status = byAnalyst.get(a)!;
    return {
      key: `ana-${a}`,
      icon: status === "ok" ? "done" : status === "failed" ? "fail" : "wait",
      label: formatAnalyst(a, lang),
      detail:
        status === "running"
          ? lang === "zh"
            ? "分析中"
            : "analyzing"
          : status === "failed"
            ? lang === "zh"
              ? "失败"
              : "failed"
            : undefined,
    };
  });
  const done = order.filter((a) => ["ok", "failed"].includes(byAnalyst.get(a)!)).length;
  return { key: "analysis", title: lang === "zh" ? "分析" : "Analysis", progress: `${done}/${order.length}`, lines };
}

/** Single-line stages (run_started, snapshot, gates, claims, ... completed). */
function singleStages(events: PipelineEvent[], lang: Lang): Stage[] {
  const stages: Stage[] = [];
  const push = (key: string, title: string, lines: StageLine[]) => {
    if (lines.length > 0) stages.push({ key, title, lines });
  };

  const line = (key: string, icon: StageLine["icon"], label: string, detail?: string): StageLine =>
    ({ key, icon, label, detail });

  // R4：Profile 收敛（§10.4）
  const profileEvent = events.find((e) => e.event === "profile_applied");
  if (profileEvent) {
    const excluded = (profileEvent.excluded_capabilities as string[] | undefined) ?? [];
    push(
      "profile",
      lang === "zh" ? "研究面（Profile）" : "Research profile",
      [
        line(
          "profile_applied",
          "done",
          `${lang === "zh" ? "采集面" : "collecting"}: ${(
            (profileEvent.capabilities as string[] | undefined) ?? []
          ).join(" / ")}${excluded.length ? (lang === "zh" ? ` · 裁剪 ${excluded.length} 项` : ` · excluded ${excluded.length}`) : ""}`,
        ),
      ],
    );
  }

  // R4：等待补充数据（§10.3）
  const waiting = events.find((e) => e.event === "waiting_data");
  if (waiting) {
    const wanted = (waiting.capabilities as string[] | undefined) ?? [];
    push(
      "waiting",
      lang === "zh" ? "等待补充数据" : "Waiting for data",
      [
        line(
          "waiting_data",
          "warn",
          `${lang === "zh" ? "补采" : "re-collecting"}: ${wanted.join(" / ") || "—"}`,
        ),
      ],
    );
  }

  // R4：复核阶段（§10.5）
  const reviewing = events.find((e) => e.event === "reviewing");
  if (reviewing) {
    push(
      "review",
      lang === "zh" ? "研究复核" : "Review",
      [line("reviewing", "done", lang === "zh" ? "反方证据与质量复核" : "contrarian + quality review")],
    );
  }

  const missingSummary = events.find((e) => e.event === "missing_data_summary");
  if (missingSummary) {
    const stillOpen = Number(missingSummary.still_open ?? 0);
    push(
      "missing",
      lang === "zh" ? "缺失数据" : "Missing data",
      [
        line(
          "missing_data_summary",
          stillOpen > 0 ? "warn" : "done",
          stillOpen > 0
            ? lang === "zh"
              ? `仍有 ${stillOpen} 项研究请求待补（下一周期继承）`
              : `${stillOpen} open research request(s)`
            : lang === "zh"
              ? "缺失项本轮已补齐"
              : "all filled this pass",
        ),
      ],
    );
  }

  const started = events.find((e) => e.event === "run_started");
  if (started) {
    push("start", lang === "zh" ? "研究启动" : "Research started", [
      line("run_started", "done", lang === "zh" ? "研究已启动" : "Research started", formatWhen(started.at, lang)),
    ]);
  }

  const snapshot = events.find((e) => e.event === "snapshot_built");
  if (snapshot) {
    push("snapshot", lang === "zh" ? "证据快照" : "Evidence snapshot", [
      line(
        "snapshot_built",
        "done",
        lang === "zh" ? "快照已构建（PIT）" : "Snapshot built (PIT)",
        `${snapshot.evidence_count ?? 0} ${lang === "zh" ? "条证据" : "evidence"}`,
      ),
    ]);
  }

  // quality gates: one line per gate, in run order, not deduped
  const gateLines: StageLine[] = events
    .filter((e) => e.event === "quality_gate")
    .map((e, i) =>
      line(
        `gate-${i}`,
        e.blocked ? "fail" : e.status === "warn" ? "warn" : "done",
        lang === "zh"
          ? e.gate === "evidence"
            ? "证据质量检查"
            : e.gate === "analysis"
              ? "分析质量检查"
              : "报告质量检查"
          : e.gate === "evidence"
            ? "Evidence gate"
            : e.gate === "analysis"
              ? "Analysis gate"
              : "Report gate",
        e.blocked ? (lang === "zh" ? "未通过" : "blocked") : undefined,
      ),
    );
  push("gates", lang === "zh" ? "质量检查" : "Quality gates", gateLines);

  const claims = events.find((e) => e.event === "claims_compiled");
  if (claims) {
    push("claims", lang === "zh" ? "主张汇总" : "Claims", [
      line(
        "claims_compiled",
        "done",
        lang === "zh" ? "主张已汇编" : "Claims compiled",
        `${claims.count ?? 0} ${lang === "zh" ? "条" : "items"}`,
      ),
    ]);
  }

  const thesis = events.find((e) => e.event === "thesis_ready");
  if (thesis) {
    const supporting = Number(thesis.supporting ?? 0);
    const opposing = Number(thesis.opposing ?? 0);
    push("thesis", lang === "zh" ? "论点构建" : "Thesis", [
      line(
        "thesis_ready",
        "done",
        lang === "zh" ? "论点已构建" : "Thesis ready",
        `${supporting}/${opposing} ${lang === "zh" ? "支撑/对立" : "support/oppose"}`,
      ),
    ]);
  }

  const debate = events.find((e) => e.event === "debate_ready");
  if (debate) {
    const skipped = debate.status === "skipped";
    push("debate", lang === "zh" ? "多空辩论" : "Debate", [
      line(
        "debate_ready",
        skipped ? "missing" : "done",
        skipped ? (lang === "zh" ? "证据不足，已跳过" : "Skipped (thin evidence)") : lang === "zh" ? "多空辩论完成" : "Debate ready",
      ),
    ]);
  }

  const valuation = events.find((e) => e.event === "valuation_ready");
  if (valuation) {
    push("valuation", lang === "zh" ? "估值计算" : "Valuation", [
      line(
        "valuation_ready",
        "done",
        lang === "zh" ? "确定性估值" : "Deterministic valuation",
        `${valuation.methods?.length ?? 0} ${lang === "zh" ? "种方法" : "methods"}`,
      ),
    ]);
  }

  const scenario = events.find((e) => e.event === "scenario_ready");
  if (scenario) {
    push("scenario", lang === "zh" ? "情景分析" : "Scenarios", [
      line("scenario_ready", "done", lang === "zh" ? "熊/基准/牛情景" : "Bear/Base/Bull",
        `${scenario.scenarios ?? 0} ${lang === "zh" ? "个情景" : "scenarios"}`),
    ]);
  }

  const risk = events.find((e) => e.event === "risk_ready");
  if (risk) {
    push("risk", lang === "zh" ? "风险评估" : "Risks", [
      line("risk_ready", "done", lang === "zh" ? "风险清单已生成" : "Risk list built",
        `${risk.risks ?? 0} ${lang === "zh" ? "项风险" : "risks"}`),
    ]);
  }

  const report = events.find((e) => e.event === "report_ready");
  if (report) {
    push("report", lang === "zh" ? "报告生成" : "Report", [
      line("report_ready", "done", lang === "zh" ? "报告已生成" : "Report ready"),
    ]);
  }

  const failed = events.find((e) => e.event === "run_failed");
  const completed = events.find((e) => e.event === "run_completed");
  if (failed) {
    push("done", lang === "zh" ? "研究失败" : "Research failed", [
      line("run_failed", "fail", lang === "zh" ? "运行失败" : "Run failed", failed.error),
    ]);
  } else if (completed) {
    push("done", lang === "zh" ? "研究完成" : "Research completed", [
      line("run_completed", "done", lang === "zh" ? "全部完成" : "Completed", formatWhen(completed.at, lang)),
    ]);
  }

  return stages;
}

/**
 * Research pipeline card (PW1): SSE drives the live view; the POST only
 * triggers the run and returns the final outcome (整改方案 §4).
 *
 * Stages group *every* event (no dedupe): each collected capability and each
 * analyst gets its own line (§5). Tech IDs stay out of the main UI (§7).
 */
export function ResearchPipelineCard({
  instrumentId,
  autoStart = false,
}: {
  instrumentId: string;
  autoStart?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang: Lang = i18n.language.startsWith("zh") ? "zh" : "en";
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      sourceRef.current?.close();
      sourceRef.current = null;
    };
  }, []);

  const startRef = useRef<(() => void) | null>(null);

  const appendEvent = (e: PipelineEvent) => {
    setEvents((prev) => [...prev, e]);
  };

  const start = () => {
    setEvents([]);
    setError(null);
    setResult(null);
    setRunning(true);
    const runId = `run_${crypto.randomUUID().slice(0, 12)}`;

    // 1) subscribe BEFORE triggering — every event lands live
    const source = new EventSource(
          `/api/v1/events/stream?run_id=${encodeURIComponent(runId)}&token=${encodeURIComponent(localStorage.getItem("asro_token") ?? "")}`,
        );
    sourceRef.current = source;
    for (const name of SSE_EVENT_NAMES) {
      source.addEventListener(name, (ev: MessageEvent) => {
        try {
          // the SSE ``event:`` field carries the stage name; data carries the
          // payload — merge them so stage builders can route by ``e.event``
          appendEvent({ event: ev.type, ...(JSON.parse(ev.data) as object) } as PipelineEvent);
        } catch {
          /* keep-alive or malformed frame — ignore, never crash the view */
        }
      });
    }
    source.addEventListener("run_completed", () => closeStream());
    source.addEventListener("run_failed", () => closeStream());
    // network drop / server restart: stop cleanly, the POST path surfaces errors
    source.onerror = () => closeStream();

    const closeStream = () => {
      source.close();
      if (sourceRef.current === source) sourceRef.current = null;
    };

    // 2) POST triggers the run; its response carries the final outcome only
    const trigger = async () => {
      try {
        const resp = await fetch(
          `/api/v1/pipeline/run?instrument=${encodeURIComponent(instrumentId)}&run_id=${encodeURIComponent(runId)}`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const body = (await resp.json().catch(() => null)) as
            | { error_code?: string; detail?: string }
            | null;
          throw new Error(body?.error_code ?? body?.detail ?? "network.unreachable");
        }
        const data = (await resp.json()) as PipelineResult;
        setResult(data);
        // §37: a sub-second run can finish before the SSE handshake lands its
        // early events — backfill the panel from the persisted replay
        try {
          const replayResp = await fetch(`/api/v1/research-runs/${runId}/events`);
          if (replayResp.ok) {
            const body = (await replayResp.json()) as {
              results: Array<{ event_type: string; at: string; payload: Record<string, unknown> }>;
            };
            const backfill = body.results.map((r) => ({
              event: r.event_type,
              at: r.at,
              ...(r.payload ?? {}),
            })) as PipelineEvent[];
            setEvents((prev) => (prev.length >= backfill.length ? prev : backfill));
          }
        } catch {
          /* replay backfill is best-effort; live events remain authoritative */
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "common.error");
      } finally {
        setRunning(false);
        closeStream();
      }
    };
    void trigger();
  };
  startRef.current = start;

  useEffect(() => {
    if (autoStart && !running && !result && startRef.current) {
      startRef.current();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart]);

  const stages = useMemo<Stage[]>(() => {
    const collected = collectStage(events, lang);
    const analysis = analysisStage(events, lang);
    const singles = singleStages(events, lang);
    const all: Stage[] = [];
    if (collected) all.push(collected);
    if (analysis) all.push(analysis);
    all.push(...singles);
    return all;
  }, [events, lang]);

  const reportId =
    result?.report_id ??
    (events.find((e) => e.event === "report_ready" || e.event === "run_completed")?.report_id as
      | string
      | undefined);

  return (
    <section className="card" data-testid="pipeline-card">
      <h2>{t("pipeline.title")}</h2>
      {!running && !result && (
        <button type="button" className="control-btn" onClick={start}>
          {t("pipeline.run")}
        </button>
      )}
      {running && <p className="secondary">{t("common.loading")}</p>}
      {error && (
        <p className="status-error mono">
          {t(`errors.${error}`, { defaultValue: t("common.error") })}
        </p>
      )}

      {stages.length > 0 && (
        <ol data-testid="pipeline-stages" className="pipeline-stages">
          {stages.map((stage) => (
            <li key={stage.key} className="pipeline-stage">
              <div className="pipeline-stage-head">
                <span>{stage.title}</span>
                {stage.progress && <span className="secondary mono">{stage.progress}</span>}
              </div>
              <ul className="pipeline-lines">
                {stage.lines.map((line) => (
                  <li key={line.key} className="result-row">
                    <span className={`stage-icon stage-${line.icon}`}>{iconChar(line.icon)}</span>
                    <span>{line.label}</span>
                    {line.detail && <span className="secondary mono">{line.detail}</span>}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      )}

      {result && !running && (
        <div data-testid="pipeline-summary">
          {result.claim_count !== undefined && (
            <p className="mono">{t("pipeline.claimsCount", { count: result.claim_count })}</p>
          )}
          <div className="header-controls">
            {reportId && (
              <button
                type="button"
                className="control-btn"
                onClick={() => navigate(`/reports/${reportId}`)}
              >
                {t("pipeline.openReport")}
              </button>
            )}
            <button
              type="button"
              className="control-btn"
              onClick={() => navigate(`/instrument/${instrumentId}`)}
            >
              {t("pipeline.openWorkspace")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
