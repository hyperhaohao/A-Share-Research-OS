import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * 产业地图/全球坐标按标的数据：Sidebar 直达时取关注池第一个标的，
 * 无关注时引导回关注池（不建空壳页面，任务书 §3）。
 */
export function WithInstrumentRedirect({
  basePath,
  children,
}: {
  basePath: string;
  children: (instrumentId: string) => React.ReactNode;
}) {
  const params = useParams();
  const instrumentId = params.instrumentId;
  const { t } = useTranslation();

  const { data, isPending } = useQuery({
    queryKey: ["watchlist-view-first"],
    enabled: instrumentId == null,
    staleTime: 30_000,
    queryFn: async (): Promise<string | null> => {
      const resp = await fetch("/api/v1/views/watchlist");
      if (!resp.ok) return null;
      const body = (await resp.json()) as { results: Array<{ instrument_id: string }> };
      return body.results[0]?.instrument_id ?? null;
    },
  });

  if (instrumentId != null) return <>{children(instrumentId)}</>;
  if (isPending) {
    return (
      <main className="page layout-canvas">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  const target = data ?? null;
  if (target) return <Navigate to={`${basePath}/${target}`} replace />;
  return (
    <main className="page layout-canvas">
      <p className="secondary">{t("industryMap.noInstrument")}</p>
      <Link to="/watchlist" className="control-btn">
        {t("nav.watchlist")}
      </Link>
    </main>
  );
}
