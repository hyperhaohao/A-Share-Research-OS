/**
 * Report revision panel (整改 R4.7): propose revision → diff → accept /
 * reject, plus version history. Real API only (POST /revisions, POST
 * /revisions/{id}/accept|reject, GET versions).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface ReportVersion {
  version_id: string;
  version_no: number;
  parent_version_id: string | null;
  change_reason: string | null;
  changed_sections: string[];
  language: string;
  markdown: string;
  created_at: string;
}

interface Proposal {
  proposal_id: string;
  status: string;
  original_text: string;
  proposed_text: string;
  reason: string;
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`http_${resp.status}`);
  return resp.json();
}

export function RevisionPanel({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [originalText, setOriginalText] = useState("");
  const [proposedText, setProposedText] = useState("");
  const [reason, setReason] = useState("");
  const [selectedSection, setSelectedSection] = useState("executive_summary");

  const chainQuery = useQuery({
    queryKey: ["report-versions", reportId],
    queryFn: () =>
      fetchJson<{ count: number; results: ReportVersion[] }>(
        `/api/v1/reports/${reportId}/versions`,
      ),
  });

  const proposeMutation = useMutation({
    mutationFn: async () => {
      const chain = chainQuery.data!.results;
      const base = chain[chain.length - 1];
      const resp = await fetch(`/api/v1/reports/${reportId}/revisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_version_id: base.version_id,
          target_section: selectedSection,
          original_text: originalText,
          proposed_text: proposedText,
          reason,
        }),
      });
      if (!resp.ok) throw new Error(`http_${resp.status}`);
      return resp.json() as Promise<{ proposal: Proposal }>;
    },
    onSuccess: () => {
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["revisions", reportId] });
    },
  });

  const acceptMutation = useMutation({
    mutationFn: async (proposalId: string) => {
      const resp = await fetch(`/api/v1/revisions/${proposalId}/accept`, { method: "POST" });
      if (!resp.ok) throw new Error(`http_${resp.status}`);
      return resp.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report-versions", reportId] });
      queryClient.invalidateQueries({ queryKey: ["revisions", reportId] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (proposalId: string) => {
      const resp = await fetch(`/api/v1/revisions/${proposalId}/reject`, { method: "POST" });
      if (!resp.ok) throw new Error(`http_${resp.status}`);
      return resp.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["revisions", reportId] }),
  });

  const revisionsQuery = useQuery({
    queryKey: ["revisions", reportId],
    queryFn: () =>
      fetchJson<{ count: number; results: Proposal[] }>(
        `/api/v1/reports/${reportId}/revisions`,
      ),
  });

  const pending = revisionsQuery.data?.results.filter((p) => p.status === "proposed") ?? [];

  return (
    <div className="card" data-testid="revision-panel">
      <h2>{t("revision.title")}</h2>

      {/* version history */}
      <p className="control-label">{t("revision.versions")}</p>
      <ul>
        {(chainQuery.data?.results ?? []).map((v) => (
          <li key={v.version_id} className="result-row">
            <span className="mono">v{v.version_no}</span>
            <span className="mono secondary">{v.language}</span>
            <span className="secondary">
              {v.change_reason ?? t("revision.initialVersion")}
            </span>
          </li>
        ))}
      </ul>

      <button className="control-btn" onClick={() => setShowForm(!showForm)}>
        {t("revision.propose")}
      </button>

      {showForm && (
        <div data-testid="revision-form">
          <p className="control-label">{t("revision.section")}</p>
          <select
            className="control-btn"
            value={selectedSection}
            onChange={(e) => setSelectedSection(e.target.value)}
          >
            {["executive_summary", "market_and_capital", "valuation", "risks"].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <p className="control-label">{t("revision.original")}</p>
          <textarea
            value={originalText}
            onChange={(e) => setOriginalText(e.target.value)}
            rows={2}
            style={{ width: "100%" }}
          />
          <p className="control-label">{t("revision.proposed")}</p>
          <textarea
            value={proposedText}
            onChange={(e) => setProposedText(e.target.value)}
            rows={2}
            style={{ width: "100%" }}
          />
          <p className="control-label">{t("revision.reason")}</p>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{ width: "100%" }}
          />
          <button
            className="control-btn"
            style={{ marginTop: 8 }}
            disabled={
              proposeMutation.isPending ||
              !originalText ||
              !proposedText ||
              originalText === proposedText ||
              !reason
            }
            onClick={() => proposeMutation.mutate()}
          >
            {t("revision.submit")}
          </button>
          {proposeMutation.isError && (
            <p className="status-error">{t("common.error")}</p>
          )}
        </div>
      )}

      {/* pending proposals with diff + accept/reject */}
      {pending.length > 0 && (
        <div data-testid="pending-revisions">
          <p className="control-label">{t("revision.pending")}</p>
          {pending.map((p) => (
            <div key={p.proposal_id} className="card">
              <p className="mono secondary">{p.proposal_id}</p>
              <p>
                <span className="status-error">{p.original_text}</span>
                {" → "}
                <span className="status-ok">{p.proposed_text}</span>
              </p>
              <p className="secondary">{p.reason}</p>
              <div className="header-controls">
                <button
                  className="control-btn"
                  onClick={() => acceptMutation.mutate(p.proposal_id)}
                  disabled={acceptMutation.isPending}
                >
                  {t("revision.accept")}
                </button>
                <button
                  className="control-btn"
                  onClick={() => rejectMutation.mutate(p.proposal_id)}
                  disabled={rejectMutation.isPending}
                >
                  {t("revision.reject")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
