import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PredictionCreateButton } from "../components/PredictionCreateButton";
import { ReportLineage } from "../components/ReportLineage";
import { useInstrumentName } from "../shared/instrument";
import { formatGate, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

interface ReportSummary {
  report_id: string;
  instrument_id: string;
  snapshot_id: string;
  language: string;
  gate_status: string;
  created_at: string | null;
  latest_version_no: number;
}

interface ThesisSummary {
  thesis_id: string;
  supporting_claims: string[];
  opposing_claims: string[];
}

async function fetchReports(): Promise<ReportSummary[]> {
  const resp = await fetch("/api/v1/reports");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
}

/** 研究判断 derived from the snapshot's own thesis claim counts. */
function useJudgment(instrumentId: string | null, snapshotId: string | null) {
  const { data } = useQuery({
    queryKey: ["judgment", instrumentId, snapshotId],
    enabled: instrumentId != null && snapshotId != null,
    staleTime: 60000,
    queryFn: async (): Promise<ThesisSummary | null> => {
      const params = new URLSearchParams({ instrument_id: instrumentId ?? "" });
      if (snapshotId) params.set("snapshot_id", snapshotId);
      const resp = await fetch(`/api/v1/theses?${params.toString()}`);
      if (!resp.ok) return null;
      const body = await resp.json();
      return (body.results?.[0] as ThesisSummary) ?? null;
    },
  });
  if (!data) return null;
  const s = data.supporting_claims?.length ?? 0;
  const o = data.opposing_claims?.length ?? 0;
  if (s === 0 && o === 0) return null;
  return s > o ? "up" : o > s ? "down" : "neutral";
}

function ReportCard({ report }: { report: ReportSummary }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const judgment = useJudgment(report.instrument_id, report.snapshot_id);

  const profile = useInstrumentName(report.instrument_id);

  return (
    <li className="card watch-card" data-testid="report-card">
      <div className="watch-card-head">
        <Link to={`/reports/${report.report_id}`} className="watch-card-name">
          {profile?.name ?? report.instrument_id}
          {profile ? ` · ${profile.code}` : ""}
        </Link>
        <span className="secondary">{t("report.fullTitle")}</span>
      </div>

      <div className="task-grid">
        <span>{t("report.dateLabel")}</span>
        <span>{formatWhen(report.created_at, lang)}</span>
        <span>{t("report.judgmentLabel")}</span>
        <span>{judgment ? t(`workspace.direction.${judgment}`) : "—"}</span>
        <span>{t("report.versionLabel")}</span>
        <span className="mono">v{report.latest_version_no}</span>
        <span>{t("report.qualityLabel")}</span>
        <span>{formatGate(report.gate_status, lang)}</span>
      </div>

      <ReportLineage reportId={report.report_id} />

      <div className="header-controls">
        <Link className="control-btn" to={`/reports/${report.report_id}`}>
          {t("report.open")}
        </Link>
        <PredictionCreateButton
          reportId={report.report_id}
          instrumentId={report.instrument_id}
        />
      </div>
    </li>
  );
}

/** Reports list — business cards over the real report library (PW2 §18). */
export function ReportsPage() {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  return (
    <main className="page" data-testid="reports-page">
      <h1>{t("nav.reports")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("label.no_data")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list watch-cards">
          {data.map((r) => (
            <ReportCard key={r.report_id} report={r} />
          ))}
        </ul>
      )}
    </main>
  );
}
