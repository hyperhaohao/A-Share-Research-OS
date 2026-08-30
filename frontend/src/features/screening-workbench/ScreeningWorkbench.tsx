import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import { StrategyLaunchButton } from "../../components/StrategyLaunchButton";

/**
 * 智能选股工作台（Guanlan Direct Port G5，方案 §16/§36）：
 * 左 条件侧栏（真实筛选规则 + 逐规则排除计数）/ 中 候选池（排名/评级）/
 * 右 研究解释 Inspector（Why Selected + 风险 + 进入研究/加入关注/做成策略）。
 * 数据全部来自 ASRO screening run（真实研究状态求值，方案 §45）。
 */

interface Candidate {
  instrument_id: string;
  code: string;
  name: string;
  rank: number;
  score: number;
  matched_rules: string[];
  explanation: string;
  risks: string[];
  experience_card_refs: string[];
}

interface ScreeningRun {
  run_id: string;
  card_id: string | null;
  universe_size: number;
  rules: Array<Record<string, unknown>>;
  candidates: Candidate[];
  excluded_summary: Record<string, unknown>;
  status: string;
  error: string | null;
  created_at: string | null;
}

export function ScreeningWorkbench() {
  const params = useParams();
  const runId = params.runId ?? "";
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isPending, isError } = useQuery({
    queryKey: ["screening-run", runId],
    enabled: runId !== "",
    refetchInterval: 2000,
    queryFn: async (): Promise<ScreeningRun> => {
      const resp = await fetch(`/api/v1/screening-runs/${runId}`);
      if (!resp.ok) throw new Error("screening.not_found");
      const body = (await resp.json()) as { run: ScreeningRun };
      return body.run;
    },
  });

  if (isPending) {
    return (
      <main className="page" data-testid="screening-detail">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError || !data) {
    return (
      <main className="page" data-testid="screening-detail">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }

  const excluded = data.excluded_summary as {
    universe_size?: number;
    candidate_count?: number;
    excluded_by_rule?: Record<string, number>;
    examples?: Record<string, string>;
  };
  const selected = data.candidates.find((c) => c.instrument_id === selectedId) ?? null;

  return (
    <main className="page" data-testid="screening-detail">
      <p>
        <Link to="/screening" className="secondary">← {t("nav.screening")}</Link>
      </p>
      <div className="watch-card-head">
        <h1>{t("screening.detailTitle")}</h1>
        {data.status === "completed" && data.candidates.length > 0 && (
          <StrategyLaunchButton screeningRunId={data.run_id} />
        )}
      </div>
      <p className="secondary">
        {t("screening.universeSize", { universe: data.universe_size })} ·{" "}
        {t("screening.candidateCount", { count: data.candidates.length })} ·{" "}
        {formatWhen(data.created_at, lang)}
      </p>

      {data.status === "running" && <p className="secondary">{t("workflow.running")}</p>}
      {data.status === "failed" && (
        <p className="status-error">{t("workflow.failed")}: {data.error}</p>
      )}

      {data.status === "completed" && (
        <div className="sw-grid">
          <aside className="sw-col-rules">
            <Panel title={t("screenWs.rulesTitle")} hint={data.card_id ? t("screenWs.fromCard") : undefined}>
              <ul className="watch-list" data-testid="screening-rules">
                {data.rules.map((r, i) => {
                  const kind = String(r.kind ?? "");
                  const count = excluded?.excluded_by_rule?.[kind];
                  return (
                    <li key={i} className="result-row">
                      <span>{t(`screening.rule.${kind}`)}</span>
                      <span className="secondary mono">
                        {r.min_reports != null ? `min=${String(r.min_reports)}` : ""}
                        {r.direction != null &&
                        String(r.direction) !== "any" &&
                        String(r.direction).length > 0
                          ? String(r.direction)
                          : ""}
                      </span>
                      {count != null && (
                        <Badge tone="neutral">
                          {t("screenWs.excludedN", { count: Number(count) })}
                        </Badge>
                      )}
                    </li>
                  );
                })}
              </ul>
              {data.card_id && (
                <p className="secondary sw-card-link">
                  <Link to={`/experience/${data.card_id}`}>{t("screenWs.openSourceCard")} →</Link>
                </p>
              )}
            </Panel>

            <Panel title={t("screenWs.excludedTitle")}>
              <div data-testid="screening-excluded">
                <ul className="watch-list">
                  {Object.entries(excluded?.excluded_by_rule ?? {}).map(([kind, count]) => (
                    <li key={kind} className="result-row">
                      <span className="secondary">{t(`screening.rule.${kind}`)}</span>
                      <span className="mono">{count}</span>
                      <span className="secondary sw-example">
                        {excluded?.examples?.[kind] ? `例：${excluded.examples[kind]}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </Panel>
          </aside>

          <div className="sw-col-candidates">
            <table className="data-table" data-testid="screening-candidates">
              <thead>
                <tr>
                  <th>{t("screening.colRank")}</th>
                  <th>{t("screening.colInstrument")}</th>
                  <th>{t("screening.colScore")}</th>
                  <th>{t("screening.colMatched")}</th>
                  <th>{t("screening.colRisk")}</th>
                </tr>
              </thead>
              <tbody>
                {data.candidates.map((c) => (
                  <tr
                    key={c.instrument_id}
                    data-testid="screening-candidate"
                    className={c.instrument_id === selectedId ? "sw-row-selected" : ""}
                    onClick={() => setSelectedId(c.instrument_id)}
                  >
                    <td className="mono">
                      #{c.rank}
                      {c.rank <= 3 && data.candidates.length > 3 && (
                        <Badge tone="ok">{t("screenWs.topRated")}</Badge>
                      )}
                    </td>
                    <td>
                      <Link to={`/instrument/${c.instrument_id}`}>{c.name}</Link>
                    </td>
                    <td className="mono">{c.score}</td>
                    <td className="secondary">{c.matched_rules.join("；")}</td>
                    <td className="secondary">{c.risks.join("；") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.candidates.length === 0 && (
              <p className="secondary">{t("screening.noCandidates")}</p>
            )}
          </div>

          <aside className="sw-col-inspector">
            <CandidateInspector candidate={selected} candidateCount={data.candidates.length} />
          </aside>
        </div>
      )}
    </main>
  );
}

/** 研究解释 Inspector（方案 §16：Why Selected + 进入研究/加入关注/做成策略）。 */
function CandidateInspector({
  candidate,
  candidateCount,
}: {
  candidate: Candidate | null;
  candidateCount: number;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const watchM = useMutation({
    mutationFn: async (instrumentId: string) => {
      const resp = await fetch("/api/v1/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instrument: instrumentId }),
      });
      if (!resp.ok && resp.status !== 409) throw new Error("network.unreachable");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  if (!candidate) {
    return (
      <Panel title={t("screenWs.inspectorTitle")}>
        <p className="secondary">{t("screenWs.inspectorEmpty")}</p>
      </Panel>
    );
  }

  const percentile =
    candidateCount > 0
      ? Math.round(((candidateCount - candidate.rank + 1) / candidateCount) * 100)
      : null;

  return (
    <Panel
      title={t("screenWs.inspectorTitle")}
      hint={`#${candidate.rank}${percentile != null ? ` · ${t("screenWs.percentile", { pct: percentile })}` : ""}`}
    >
      <div className="sw-inspector" data-testid="screening-candidate-inspector">
        <div className="cc-brief-head">
          <div>
            <div className="cc-brief-name serif">{candidate.name}</div>
            <div className="secondary mono cc-brief-code">{candidate.code}</div>
          </div>
          <Badge tone="ok">{t("screenWs.whySelected")}</Badge>
        </div>

        <p className="sw-explanation">{candidate.explanation}</p>

        <section className="ew-refine-section">
          <h4 className="ew-refine-label">{t("screenWs.matchedRules")}</h4>
          <ul className="ew-cond-list">
            {candidate.matched_rules.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </section>

        <section className="ew-refine-section">
          <h4 className="ew-refine-label">{t("screening.colRisk")}</h4>
          {candidate.risks.length === 0 ? (
            <p className="secondary">—</p>
          ) : (
            <ul className="ew-cond-list ew-cond-invalid">
              {candidate.risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </section>

        <div className="sw-cta">
          <Link className="gl-button" to={`/instrument/${candidate.instrument_id}`}>
            {t("screenWs.enterResearch")} →
          </Link>
          <Button
            data-testid="screening-add-watchlist"
            disabled={watchM.isPending}
            onClick={() => watchM.mutate(candidate.instrument_id)}
          >
            {watchM.isSuccess ? t("screenWs.addedToWatchlist") : t("screenWs.addToWatchlist")}
          </Button>
        </div>
      </div>
    </Panel>
  );
}
