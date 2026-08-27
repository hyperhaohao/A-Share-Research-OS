import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useTheme } from "../theme/ThemeProvider";
import { InstrumentSearch } from "../components/InstrumentSearch";
import type { ResolvedTheme } from "../theme/theme";

/** Health probe — real backend call, no mock data. */
async function fetchHealth(): Promise<{ status: string; version: string }> {
  const resp = await fetch("/api/v1/health");
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    const code = body?.error_code ?? "network.unreachable";
    throw new Error(code);
  }
  return resp.json();
}

function BackendStatus() {
  const { t } = useTranslation();
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: 1,
  });

  if (isPending) return <span className="mono">{t("common.loading")}</span>;
  if (isError)
    return (
      <span className="status-error mono">
        {t("home.backendUnreachable")} · {t(`errors.${error.message}`, { defaultValue: t("common.error") })}{" "}
        <button type="button" className="control-btn" onClick={() => refetch()}>
          {t("home.checkAgain")}
        </button>
      </span>
    );
  return (
    <span className="status-ok mono">
      ok · v{data.version}
    </span>
  );
}

export function HomePage() {
  const { t } = useTranslation();
  const { preference, resolved } = useTheme();

  return (
    <main className="page">
      <h1>{t("home.title")}</h1>
      <p className="secondary">{t("home.description")}</p>

      <section className="card">
        <h2>{t("home.backendStatus")}</h2>
        <BackendStatus />
      </section>

      <section className="card">
        <h2>{t("home.currentTheme")}</h2>
        <p data-testid="theme-state" className="mono">
          {preference === "system"
            ? t("home.themeFollowsSystem", { theme: resolved })
            : t("home.currentThemeValue", { theme: resolved })}
        </p>
      </section>

      <InstrumentSearch />

      <section className="card">
        <h2>{t("home.sampleQuote")}</h2>
        <p>
          <span className="quote-up" data-testid="up-sample">
            {t("home.upSample")}
          </span>
          {"  "}
          <span className="quote-down" data-testid="down-sample">
            {t("home.downSample")}
          </span>
        </p>
      </section>
    </main>
  );
}

export type { ResolvedTheme };
