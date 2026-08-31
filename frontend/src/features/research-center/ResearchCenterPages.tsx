import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, Button, Panel } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";

/* Research Inbox / Memory / Thesis Center UI（R8-C8，方案 §12/§13/§16.5） */

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("network.unreachable");
  return resp.json();
}

/* ── Research Inbox ── */
export function ResearchInboxPage() {
  const { t } = useTranslation();
  const { data, isPending } = useQuery({
    queryKey: ["research-inbox"],
    refetchInterval: 30000,
    queryFn: () => fetchJson<{ inbox: Record<string, unknown> }>("/api/v1/research-inbox"),
  });
  const inbox = data?.inbox;

  return (
    <main className="page" data-testid="research-inbox-page">
      <h1>{t("researchCenter.inboxTitle")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {inbox && (
        <div className="rc-grid">
          <Panel title={t("researchCenter.newEvidence")}>
            {(inbox.new_evidence as never[]).length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(inbox.new_evidence as {evidence_id:string;instrument_id:string;title:string;at:string}[]).map(e => (
                  <li key={e.evidence_id} className="result-row">
                    <Link to={`/instrument/${encodeURIComponent(e.instrument_id)}`}>{e.title?.slice(0,60)}</Link>
                    <span className="secondary mono">{e.at?.slice(0,10)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.materiality")}>
            {(inbox.materiality_alerts as never[]).length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(inbox.materiality_alerts as {instrument_id:string;decision:string}[]).map((m,i) => (
                  <li key={i} className="result-row"><span>{m.instrument_id}</span><Badge tone="warning">{m.decision}</Badge></li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.requests")}>
            {(inbox.open_research_requests as never[]).length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(inbox.open_research_requests as {instrument_id:string;capability:string}[]).map((r,i) => (
                  <li key={i} className="result-row"><span>{r.instrument_id}</span><span className="secondary">{r.capability}</span></li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title={t("researchCenter.failedCollections")}>
            {(inbox.failed_collections as never[]).length === 0 ? <p className="secondary">—</p> : (
              <ul className="watch-list">
                {(inbox.failed_collections as {instrument_id:string;capability:string;status:string}[]).map((f,i) => (
                  <li key={i} className="result-row"><span className="status-error">{f.instrument_id}</span><span className="secondary">{f.capability}</span></li>
                ))}
              </ul>
            )}
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
  status: string;
  version: number;
}

/* ── Research Memory ── */
export function ResearchMemoryPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [filter, setFilter] = useState("");
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
  const promote = useMutation({
    mutationFn: (id: string) => fetch(`/api/v1/memories/${id}/promote`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] });
      qc.invalidateQueries({ queryKey: ["memories-candidates"] });
    },
  });
  const types = ["company","industry","event_playbook","research_method","known_failure","research_checklist","user_preference"];
  const active = data?.results ?? [];
  const candidates = candData?.results ?? [];

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
              <li key={m.memory_id} className="result-row"><span>{m.title}</span><span className="secondary mono">v{m.version}</span></li>
            ))}</ul>
          )}
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
  meta: { parent_thesis_id?: string; revision_reason?: string };
  created_at: string | null;
}

/* ── Thesis Center ── */
export function ThesisCenterPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const [iid, setIid] = useState("SZSE:000831");
  const { data } = useQuery({
    queryKey: ["thesis-history", iid],
    enabled: iid !== "",
    queryFn: () => fetchJson<{ current_thesis_id: string; versions: ThesisVersion[] }>(
      `/api/v1/research-inbox/thesis-history/${encodeURIComponent(iid)}`
    ),
  });
  const versions = data?.versions ?? [];
  const current = versions.find(v => v.is_current) ?? versions[0];

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
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      )}
    </main>
  );
}
