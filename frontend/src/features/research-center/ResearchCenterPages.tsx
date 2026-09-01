import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";

/* Research Inbox / Memory / Thesis Center UI（R8-C8 → F12 产品化，§10） */

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("network.unreachable");
  return resp.json();
}

/* ── Research Inbox（F12 §10.2：全聚合面板 + 行动入口） ── */
export function ResearchInboxPage() {
  const { t } = useTranslation();
  const { data, isPending } = useQuery({
    queryKey: ["research-inbox"],
    refetchInterval: 30000,
    queryFn: () => fetchJson<{ inbox: Record<string, unknown> }>("/api/v1/research-inbox"),
  });
  const inbox = data?.inbox;
  const list = (key: string): unknown[] => ((inbox?.[key] as unknown[]) ?? []);

  return (
    <main className="page" data-testid="research-inbox-page">
      <h1>{t("researchCenter.inboxTitle")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {inbox && (
        <div className="rc-grid">
          <Panel title={t("researchCenter.newEvidence")}>
            {list("new_evidence").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("new_evidence") as {evidence_id:string;instrument_id:string;title:string;at:string}[]).map(e => (
                  <li key={e.evidence_id} className="result-row">
                    <Link to={`/instrument/${encodeURIComponent(e.instrument_id)}`}>{e.title?.slice(0,60)}</Link>
                    <span className="secondary mono">{e.at?.slice(0,10)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.materiality")}>
            {list("materiality_alerts").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("materiality_alerts") as {instrument_id:string;decision:string}[]).map((m,i) => (
                  <li key={i} className="result-row"><span>{m.instrument_id}</span><Badge tone="warning">{m.decision}</Badge></li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.requests")}>
            {list("open_research_requests").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("open_research_requests") as {instrument_id:string;capability:string}[]).map((r,i) => (
                  <li key={i} className="result-row"><span>{r.instrument_id}</span><span className="secondary">{r.capability}</span></li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.failedCollections")}>
            {list("failed_collections").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("failed_collections") as {instrument_id:string;capability:string;status:string}[]).map((f,i) => (
                  <li key={i} className="result-row"><span className="status-error">{f.instrument_id}</span><span className="secondary">{f.capability}</span></li>
                ))}
              </ul>
            )}
          </Panel>

          {/* F12 §10.2 新增聚合 */}
          <Panel title={t("researchCenter.thesisChanges")}>
            {list("thesis_changes").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("thesis_changes") as {thesis_id:string;instrument_id:string;title:string;is_current:boolean}[]).map(c => (
                  <li key={c.thesis_id} className="result-row">
                    <Link to="/thesis">{c.title?.slice(0,50)}</Link>
                    <span className="secondary mono">{c.instrument_id}</span>
                    {c.is_current && <Badge tone="ok">{t("researchCenter.current")}</Badge>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.signalHits")}>
            {list("signal_ladder_hits").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("signal_ladder_hits") as {instrument_id:string;signal_level:string;rule_id:string}[]).map((h,i) => (
                  <li key={i} className="result-row">
                    <span className="mono">{h.instrument_id}</span>
                    <Badge tone={h.signal_level === "A" ? "error" : "warning"}>{h.signal_level}</Badge>
                    <span className="secondary">{h.rule_id}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.predictionsDue")}>
            {list("predictions_due").length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(list("predictions_due") as {prediction_id:string;instrument_id:string;due_at?:string}[]).map((p,i) => (
                  <li key={i} className="result-row">
                    <Link to="/predictions">{String(p.prediction_id).slice(0,16)}</Link>
                    <span className="secondary mono">{p.instrument_id}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.nextActions")}>
            {(inbox as {recommended_actions?: string[]}).recommended_actions?.length ? (
              <ul className="watch-list">
                {(inbox.recommended_actions as string[]).map((a, i) => (
                  <li key={i} className="result-row"><span>{a}</span></li>
                ))}
              </ul>
            ) : (
              <p className="secondary">—</p>
            )}
            {/* §10.2 行动入口：一键进帷幄 */}
            <p>
              <Link to="/" className="secondary">{t("researchCenter.openInCommander")} →</Link>
            </p>
          </Panel>
        </div>
      )}
    </main>
  );
}

interface MemoryItem {
  memory_id: string;
  memory_type: string;
  title: string;
  content: string;
  status: string;
  version: number;
  scope: { tags?: string[]; instrument_id?: string | null };
  source_artifacts: string[];
  source_experiences: string[];
  created_at: string | null;
  updated_at: string | null;
}

/* ── Research Memory（F12 §10.3：candidate/active/retired + provenance 治理） ── */
export function ResearchMemoryPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["memories"] });
    qc.invalidateQueries({ queryKey: ["memories-candidates"] });
    qc.invalidateQueries({ queryKey: ["memories-retired"] });
  };
  const { data } = useQuery({
    queryKey: ["memories", filter],
    queryFn: () => fetchJson<{ count: number; results: MemoryItem[] }>(
      `/api/v1/memories?status=active${filter ? `&memory_type=${filter}` : ""}`
    ),
  });
  const { data: candData } = useQuery({
    queryKey: ["memories-candidates"],
    queryFn: () => fetchJson<{ count: number; results: MemoryItem[] }>(
      "/api/v1/memories?status=candidate"
    ),
  });
  const { data: retiredData } = useQuery({
    queryKey: ["memories-retired"],
    queryFn: () => fetchJson<{ count: number; results: MemoryItem[] }>(
      "/api/v1/memories?status=retired"
    ),
  });
  const promote = useMutation({
    mutationFn: (id: string) => fetch(`/api/v1/memories/${id}/promote`, { method: "POST" }),
    onSuccess: invalidate,
  });
  const types = ["company","industry","event_playbook","research_method","known_failure","research_checklist","user_preference"];
  const active = data?.results ?? [];
  const candidates = candData?.results ?? [];
  const retired = retiredData?.results ?? [];

  return (
    <main className="page" data-testid="research-memory-page">
      <h1>{t("researchCenter.memoryTitle")}</h1>
      <div className="rc-grid">
        <Panel title={t("researchCenter.candidates")} hint={`${candidates.length}`}>
          {candidates.length === 0 ? <p className="secondary">—</p> : (
            <ul className="watch-list">{candidates.map(m => (
              <li key={m.memory_id} className="result-row">
                <span>{m.title}</span>
                <Button onClick={() => promote.mutate(m.memory_id)}>{t("researchCenter.promote")}</Button>
              </li>
            ))}</ul>
          )}
        </Panel>
        <Panel title={t("researchCenter.active")} hint={`${active.length}`}>
          {active.length === 0 ? <p className="secondary">—</p> : (
            <ul className="watch-list">{active.map(m => (
              <li key={m.memory_id} className="result-row">
                <span>{m.title}</span>
                <span className="secondary mono">v{m.version}</span>
                {/* §10.3：active 可退役（人工治理） */}
                <Button onClick={() => promote.mutate(m.memory_id)}>{t("researchCenter.retire")}</Button>
              </li>
            ))}</ul>
          )}
        </Panel>
        <Panel title={t("researchCenter.retired")} hint={`${retired.length}`}>
          {retired.length === 0 ? <p className="secondary">—</p> : (
            <ul className="watch-list">{retired.map(m => (
              <li key={m.memory_id} className="result-row">
                <span className="secondary">{m.title}</span>
                <span className="secondary mono">v{m.version}</span>
              </li>
            ))}</ul>
          )}
        </Panel>
        <Panel title={t("researchCenter.provenance")}>
          <ul className="watch-list">
            {[...active, ...candidates].slice(0, 8).map(m => (
              <li key={"prov-" + m.memory_id} className="result-row">
                <span>{m.title?.slice(0, 40)}</span>
                <span className="secondary mono">
                  {m.source_artifacts?.slice(0, 2).join(" · ") || "—"}
                </span>
                <span className="secondary mono">
                  {formatWhen(m.updated_at, lang)}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="rc-filter">
        {types.map(tp => (
          <button key={tp} className={filter===tp ? "gl-button gl-button-primary" : "gl-button"} onClick={() => setFilter(filter===tp?"":tp)}>
            {t(`researchCenter.type.${tp}`)}
          </button>
        ))}
      </div>
    </main>
  );
}

interface ThesisVersion {
  thesis_id: string; title: string; snapshot_id: string; is_current: boolean;
  meta: {
    parent_thesis_id?: string; revision_reason?: string; revision_at?: string;
    carried_forward_claims?: string[]; revised_claim_ids?: string[];
    superseded_claim_ids?: string[]; added_evidence_ids?: string[];
  };
  created_at: string | null;
}

interface ClaimLineage {
  claim_id: string;
  statement?: string;
  revision_kind?: string | null;
  source_impact_relation?: string | null;
  confidence_level?: string | null;
  carried_forward?: boolean;
  parent_claim_id?: string | null;
}

/* ── Thesis Center（F12 §10.1：版本链 + 修订元数据 + Claim lineage diff） ── */
export function ThesisCenterPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [iid, setIid] = useState("SZSE:000831");
  const [compareTo, setCompareTo] = useState<string | null>(null);
  const { data } = useQuery({
    queryKey: ["thesis-history", iid],
    enabled: iid !== "",
    queryFn: () => fetchJson<{ current_thesis_id: string; versions: ThesisVersion[] }>(
      `/api/v1/research-inbox/thesis-history/${encodeURIComponent(iid)}`
    ),
  });
  const versions = data?.versions ?? [];
  const current = versions.find(v => v.is_current) ?? versions[0];
  const parent = current?.meta?.parent_thesis_id;
  const diffQuery = useQuery({
    queryKey: ["thesis-diff", parent, current?.thesis_id],
    enabled: parent != null && current != null,
    queryFn: () => fetchJson<Record<string, unknown>>(
      `/api/v1/research-inbox/theses/${parent}/diff/${current?.thesis_id}`
    ),
  });
  const diff = diffQuery.data as {
    claim_lineage?: ClaimLineage[];
    t2?: { revision_reason?: string; carried_forward_claims?: string[];
           revised_claim_ids?: string[]; superseded_claim_ids?: string[] };
  } | undefined;
  const lineage = diff?.claim_lineage ?? [];

  return (
    <main className="page" data-testid="thesis-center-page">
      <h1>{t("researchCenter.thesisCenter")}</h1>
      <input className="control-input" value={iid} onChange={e => setIid(e.target.value)}
        placeholder="SZSE:000831" style={{ maxWidth: 240, marginBottom: 12 }} />
      {!data || versions.length === 0 ? <p className="secondary">—</p> : (
        <div className="tc-layout">
          {current && (
            <Panel title={t("researchCenter.currentThesis")} hint={current.thesis_id}>
              <p className="serif">{current.title}</p>
              {current.meta?.revision_reason && (
                <p className="secondary">{t("researchCenter.revisionReason")}: {current.meta.revision_reason}</p>
              )}
              {current.meta?.revision_at && (
                <p className="secondary mono">{formatWhen(current.meta.revision_at, lang)}</p>
              )}
              {/* §10.1 修订元数据 */}
              {(current.meta?.carried_forward_claims?.length ||
                current.meta?.revised_claim_ids?.length ||
                current.meta?.superseded_claim_ids?.length) && (
                <ul className="watch-list">
                  <li className="result-row"><span className="secondary">carried</span>
                    <span className="mono">{current.meta.carried_forward_claims?.length ?? 0}</span></li>
                  <li className="result-row"><span className="secondary">revised</span>
                    <span className="mono">{current.meta.revised_claim_ids?.length ?? 0}</span></li>
                  <li className="result-row"><span className="secondary">superseded</span>
                    <span className="mono">{current.meta.superseded_claim_ids?.length ?? 0}</span></li>
                </ul>
              )}
            </Panel>
          )}
          <Panel title={t("researchCenter.versionHistory")}>
            <ul className="watch-list" data-testid="thesis-version-history">
              {versions.map((v, i) => (
                <li key={v.thesis_id} className="result-row">
                  <span className="mono">V{i+1}</span>
                  {v.is_current && <Badge tone="ok">{t("researchCenter.current")}</Badge>}
                  <span>{v.title?.slice(0,50)}</span>
                  <span className="secondary mono">{formatWhen(v.created_at, lang)}</span>
                  {!v.is_current && current && (
                    <Button
                      data-testid={"diff-with-" + i}
                      onClick={() => setCompareTo(v.thesis_id)}
                    >
                      {t("researchCenter.diffAgainstCurrent")}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
          {compareTo != null && lineage.length > 0 && (
            <Panel title={t("researchCenter.claimLineage")}>
              <ul className="watch-list" data-testid="thesis-claim-lineage">
                {lineage.map(c => (
                  <li key={c.claim_id} className="result-row">
                    <span>{c.statement?.slice(0, 60) ?? c.claim_id}</span>
                    {c.revision_kind && <Badge tone="warning">{c.revision_kind}</Badge>}
                    {c.source_impact_relation && (
                      <Badge tone={c.source_impact_relation === "contradicts" ? "error" : "neutral"}>
                        {c.source_impact_relation}
                      </Badge>
                    )}
                    <span className="secondary mono">{c.confidence_level ?? "—"}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      )}
    </main>
  );
}
