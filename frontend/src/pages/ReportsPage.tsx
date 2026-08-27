import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface ReportSummary {
  report_id: string;
  instrument_id: string;
  language: string;
  gate_status: string;
  created_at: string;
}

async function fetchReports(): Promise<ReportSummary[]> {
  const resp = await fetch("/api/v1/reports");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
}

/** Reports list — real published/compiled reports from the backend. */
export function ReportsPage() {
  const { t } = useTranslation();
  const { data, isPending } = useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  return (
    <main className="page" data-testid="reports-page">
      <h1>{t("nav.reports")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {data && data.length === 0 && <p className="secondary">{t("label.no_data")}</p>}
      {data && data.length > 0 && (
        <ul className="watch-list">
          {data.map((r) => (
            <li key={r.report_id} className="result-row">
              <Link to={`/reports/${r.report_id}`} className="mono">
                {r.report_id}
              </Link>
              <span>{r.instrument_id}</span>
              <span className="mono secondary">{r.language}</span>
              <span className="mono secondary">{r.gate_status}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export function ReportViewPage() {
  const { reportId = "" } = useParams();
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["report", reportId],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/reports/${encodeURIComponent(reportId)}`);
      if (!resp.ok) throw new Error("report.not_found");
      const body = await resp.json();
      return body.report as { html: string; instrument_id: string; language: string; gate_status: string };
    },
  });

  if (isPending) {
    return (
      <main className="page">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError) {
    return (
      <main className="page">
        <p className="status-error">{t("common.error")}</p>
      </main>
    );
  }
  return (
    <main className="page" data-testid="report-view">
      <h1>
        {t("report.title")}: {data.instrument_id}
      </h1>
      <p className="mono secondary">
        {data.language} · {t("report.gate")}: {data.gate_status}
      </p>
      <div className="card report-html" dangerouslySetInnerHTML={{ __html: data.html }} />
      <p>
        <Link to="/reports" className="secondary">
          ← {t("nav.reports")}
        </Link>
      </p>
    </main>
  );
}
