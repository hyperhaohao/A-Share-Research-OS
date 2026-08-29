import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { formatCapability, uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

/**
 * 数据源状态（任务书 §5 系统 / §33 Diagnostics）：真实 provider 健康表。
 */

interface ProviderHealth {
  provider_id: string;
  capability: string;
  last_status: string;
  last_attempted_at: string | null;
  last_error_type: string | null;
  consecutive_failures: number;
  available: boolean;
}

const STATUS_KEY: Record<string, string> = {
  success: "sourceHealth.statusSuccess",
  failure: "sourceHealth.statusFailure",
  parse_error: "sourceHealth.statusParse",
  timeout: "sourceHealth.statusTimeout",
  network_error: "sourceHealth.statusNetwork",
  source_unavailable: "sourceHealth.statusUnavailable",
  auth_error: "sourceHealth.statusAuth",
  no_data: "sourceHealth.statusNoData",
  partial: "sourceHealth.statusPartial",
};

export function SourceHealthPage() {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const { data, isPending, isError } = useQuery({
    queryKey: ["source-health"],
    queryFn: async (): Promise<ProviderHealth[]> => {
      const resp = await fetch("/api/v1/source-health");
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { providers: ProviderHealth[] };
      return body.providers;
    },
    refetchInterval: 30_000,
  });

  return (
    <main className="page" data-testid="source-health-page">
      <h1>{t("nav.sourceHealth")}</h1>
      {isPending && <p className="secondary">{t("common.loading")}</p>}
      {isError && <p className="status-error">{t("common.error")}</p>}
      {data && (
        <table className="data-table" data-testid="source-health-table">
          <thead>
            <tr>
              <th>{t("sourceHealth.provider")}</th>
              <th>{t("sourceHealth.capability")}</th>
              <th>{t("sourceHealth.status")}</th>
              <th>{t("sourceHealth.failures")}</th>
              <th>{t("sourceHealth.lastAttempt")}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.provider_id} className={p.available ? "" : "status-error"}>
                <td className="mono">{p.provider_id}</td>
                <td>{formatCapability(p.capability, lang)}</td>
                <td>
                  {t(STATUS_KEY[p.last_status] ?? "sourceHealth.statusUnknown")}
                  {p.last_error_type ? ` (${p.last_error_type})` : ""}
                </td>
                <td className="mono">{p.consecutive_failures}</td>
                <td className="secondary">{formatWhen(p.last_attempted_at, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
