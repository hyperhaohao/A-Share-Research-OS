import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PredictionCreateButton } from "../components/PredictionCreateButton";
import { ExperienceCardCreateButton } from "../components/ExperienceCardCreateButton";
import { ReportLineage } from "../components/ReportLineage";
import { useInstrumentName } from "../shared/instrument";
import { formatGate, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

/**
 * 报告库（UX Foundation / 任务书 §19）：单请求消费 /views/report-library，
 * 名称与研究判断由后端 Read Model 装配（N+1 与前端自算 Stance 已消除）。
 */

interface ReportRowView {
  report_id: string;
  instrument_id: string;
  name: string | null;
  code: string | null;
  judgment: string | null;
  confidence: number | null;
  created_at: string | null;
  gate_status: string;
}

async function fetchReportLibrary(): Promise<ReportRowView[]> {
  const resp = await fetch("/api/v1/views/report-library");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = (await resp.json()) as { results: ReportRowView[] };
  return body.results;
}

function ReportCard({ row }: { row: ReportRowView }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const nameFallback = useInstrumentName(row.instrument_id);

  return (
    <li className="card watch-card" data-testid="report-card">
      <div className="watch-card-head">
        <Link to={`/reports/${row.report_id}`} className="watch-card-name">
          {row.name ?? nameFallback?.name ?? row.instrument_id}
          {row.code ? ` · ${row.code}` : ""}
        </Link>
        <span className="secondary">{t("report.fullTitle")}</span>
      </div>

      <div className="task-grid">
        <span>{t("report.dateLabel")}</span>
        <span>{formatWhen(row.created_at, lang)}</span>
        <span>{t("report.judgmentLabel")}</span>
        <span>
          {row.judgment
            ? `${t(`workspace.direction.${row.judgment}`)}${row.confidence != null ? ` · ${Math.round(row.confidence * 100)}%` : ""}`
            : "—"}
        </span>
        <span>{t("report.qualityLabel")}</span>
        <span>{formatGate(row.gate_status, lang)}</span>
      </div>

      <ReportLineage reportId={row.report_id} />

      <div className="header-controls">
        <Link className="control-btn" to={`/reports/${row.report_id}`}>
          {t("report.open")}
        </Link>
        <PredictionCreateButton
          reportId={row.report_id}
          instrumentId={row.instrument_id}
        />
        <ExperienceCardCreateButton
          reportId={row.report_id}
          instrumentId={row.instrument_id}
        />
      </div>
    </li>
  );
}

/** 报告库列表（PW2 §18 / UX Foundation §19）。 */
export function ReportsPage() {
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["report-library"],
    queryFn: fetchReportLibrary,
  });

  return (
    <main className="page" data-testid="reports-page">
      <h1>{t("nav.reports")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && data.length === 0 && (
        <div className="empty-state">
          <p>{t("reports.emptyTitle")}</p>
          <p className="secondary">{t("reports.emptyHint")}</p>
          <Link to="/" className="control-btn">
            {t("reports.emptyAction")}
          </Link>
        </div>
      )}
      {data && data.length > 0 && (
        <ul className="watch-list watch-cards">
          {data.map((row) => (
            <ReportCard key={row.report_id} row={row} />
          ))}
        </ul>
      )}
    </main>
  );
}
