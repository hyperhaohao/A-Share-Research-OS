import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RevisionPanel } from "../components/RevisionPanel";
import { PredictionCreateButton } from "../components/PredictionCreateButton";
import { ExperienceCardCreateButton } from "../components/ExperienceCardCreateButton";

interface ReportData {
  report_id: string;
  instrument_id: string;
  snapshot_id: string;
  language: string;
  gate_status: string;
  html: string;
  markdown: string;
  content_json: { citations?: string[] };
}

interface EvidenceDetail {
  evidence_id: string;
  source: string;
  source_type: string;
  authority_level: string;
  fact_status: string;
  available_time: string;
  summary: string;
  metadata: Record<string, unknown>;
}

interface AuditFinding {
  code: string;
  severity: string;
  message: string;
}

interface AskAnswer {
  mode: string;
  claims?: Array<{ claim_id: string; statement: string; evidence_ids: string[] }>;
  new_evidence_ids?: string[];
  removed_evidence_ids?: string[];
  affected_claim_ids?: string[];
  citations?: string[];
}

interface AuditResultData {
  findings: AuditFinding[];
  has_fail: boolean;
}

type Panel =
  | { kind: "explain"; data: AskAnswer }
  | { kind: "refresh"; data: AskAnswer }
  | { kind: "audit"; data: AuditResultData };

const SECTION_KEYS = [
  "section.executive_summary", "section.market_and_capital", "section.key_theses",
  "section.corporate_events", "section.valuation", "section.scenarios",
  "section.bull_bear", "section.risks", "section.data_quality",
  "section.source_manifest", "section.disclaimer",
];

/** Interactive report: TOC, citation viewer and review actions (任务书 §61-§62). */
export function InteractiveReportPage() {
  const { reportId = "" } = useParams();
  const { t } = useTranslation();
  const [citation, setCitation] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel | null>(null);

  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/reports/${encodeURIComponent(reportId)}`);
      if (!resp.ok) throw new Error("report.not_found");
      const body = await resp.json();
      return body.report as ReportData;
    },
    retry: false,
  });

  const citationQuery = useQuery({
    queryKey: ["evidence", citation],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/evidence/${encodeURIComponent(citation!)}`);
      if (!resp.ok) throw new Error("evidence.not_found");
      const body = await resp.json();
      return body.evidence as EvidenceDetail;
    },
    enabled: citation !== null,
  });

  const explainMutation = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/reports/${reportId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: t("report.explainQuestion"), mode: "explain" }),
      });
      if (!resp.ok) throw new Error("common.error");
      return resp.json() as Promise<AskAnswer>;
    },
    onSuccess: (data) => setPanel({ kind: "explain", data }),
  });

  const refreshMutation = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/reports/${reportId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: "", mode: "refresh" }),
      });
      if (!resp.ok) throw new Error("common.error");
      return resp.json() as Promise<AskAnswer>;
    },
    onSuccess: (data) => setPanel({ kind: "refresh", data }),
  });

  const auditMutation = useMutation({
    mutationFn: async () => {
      const resp = await fetch(`/api/v1/reports/${reportId}/audits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level: "full_report" }),
      });
      if (!resp.ok) throw new Error("common.error");
      return resp.json() as Promise<{ findings: AuditFinding[]; has_fail: boolean }>;
    },
    onSuccess: (data) => setPanel({ kind: "audit", data }),
  });

  const sections = useMemo(() => {
    const html = reportQuery.data?.html ?? "";
    const found: Array<{ key: string; anchor: string }> = [];
    let i = 0;
    for (const key of SECTION_KEYS) {
      const label = t(key);
      if (html.includes(label)) {
        found.push({ key, anchor: `sec-${i}` });
      }
      i += 1;
    }
    return found;
  }, [reportQuery.data, t]);

  const citations = reportQuery.data?.content_json?.citations ?? [];

  return (
    <main className="page" data-testid="interactive-report">
      <header className="workspace-header">
        <h1>
          {t("report.title")}: {reportQuery.data?.instrument_id ?? reportId}
        </h1>
        <span className="mono secondary">
          {reportQuery.data?.language} · {t("report.gate")}: {reportQuery.data?.gate_status}
        </span>
      </header>

      {/* Text actions (任务书 §61) + prediction handoff (PW2 §17) */}
      <div className="report-actions" role="group" aria-label={t("report.actions")}>
        <PredictionCreateButton reportId={reportId} instrumentId={reportQuery.data?.instrument_id ?? null} />
        <ExperienceCardCreateButton reportId={reportId} instrumentId={reportQuery.data?.instrument_id ?? null} />
        <button type="button" className="control-btn" onClick={() => explainMutation.mutate()} disabled={explainMutation.isPending}>
          {t("report.explain")}
        </button>
        <button type="button" className="control-btn" onClick={() => auditMutation.mutate()} disabled={auditMutation.isPending}>
          {t("report.audit")}
        </button>
        <button type="button" className="control-btn" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
          {t("report.refresh")}
        </button>
      </div>

      {panel?.kind === "explain" && (
        <section className="card" data-testid="explain-panel">
          <h2>{t("report.explain")}</h2>
          <ul>
            {(panel.data.claims ?? []).map((c) => (
              <li key={c.claim_id}>
                {c.statement} <span className="mono secondary">[{c.evidence_ids.join(", ")}]</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {panel?.kind === "audit" && (
        <section className="card" data-testid="audit-panel">
          <h2>{t("report.audit")}</h2>
          <ul>
            {(panel.data.findings ?? []).map((f, i) => (
              <li key={i} className={f.severity === "fail" ? "status-error" : "secondary"}>
                [{f.severity}] {f.code}: {f.message}
              </li>
            ))}
          </ul>
        </section>
      )}
      {panel?.kind === "refresh" && (
        <section className="card" data-testid="refresh-panel">
          <h2>{t("report.refresh")}</h2>
          <p>{t("report.refreshNew")}: {(panel.data.new_evidence_ids ?? []).length}</p>
          <p>{t("report.refreshRemoved")}: {(panel.data.removed_evidence_ids ?? []).length}</p>
          <p>{t("report.refreshAffected")}: {(panel.data.affected_claim_ids ?? []).join(", ") || "—"}</p>
        </section>
      )}

      {/* Report body */}
      {reportQuery.data && (
        <div className="report-layout">
          <nav className="report-toc" aria-label={t("report.toc")}>
            <h2>{t("report.toc")}</h2>
            <ul>
              {sections.map((s) => (
                <li key={s.anchor}>
                  <a href={`#${s.anchor}`} onClick={(e) => {
                    e.preventDefault();
                    document.getElementById(s.anchor)?.scrollIntoView({ behavior: "smooth" });
                  }}>
                    {t(s.key)}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          <div className="report-body card report-html" dangerouslySetInnerHTML={{ __html: reportQuery.data.html }} />
        </div>
      )}

      {/* Citation viewer (任务书 §62) */}
      {citations.length > 0 && (
        <section className="card">
          <h2>{t("report.citations")}</h2>
          <ul className="watch-list">
            {citations.map((c) => (
              <li key={c} className="result-row">
                <button type="button" className="control-btn mono" onClick={() => setCitation(c)}>
                  [{c.slice(0, 18)}…]
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {citation && (
        <div className="card citation-viewer" data-testid="citation-viewer">
          <h2>{t("report.citation")}: <span className="mono">{citation}</span></h2>
          {citationQuery.data ? (
            <ul>
              <li>{t("report.citSource")}: {citationQuery.data.source} ({citationQuery.data.source_type})</li>
              <li>{t("report.citAuthority")}: {citationQuery.data.authority_level}</li>
              <li>{t("report.citFactStatus")}: {citationQuery.data.fact_status}</li>
              <li>{t("report.citAvailable")}: {citationQuery.data.available_time.slice(0, 16)}</li>
              <li>{citationQuery.data.summary}</li>
            </ul>
          ) : (
            <p className="secondary">{t("common.loading")}</p>
          )}
          <button type="button" className="control-btn" onClick={() => setCitation(null)}>
            {t("graph.close")}
          </button>
        </div>
      )}

      <p>
        <Link to="/reports" className="secondary">← {t("nav.reports")}</Link>
      </p>
          <RevisionPanel reportId={reportId} />
</main>
  );
}
