import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { newResearchContext } from "../shared/context";
import { artifactByDomain, handoffPath, recordHandoff } from "../shared/handoff";
import { formatWhen } from "../presentation/format";

/**
 * 产业研究地图 + 全球宏观坐标（V2 Phase H, §11/§52/§77）。
 * 不是孤立 Dashboard：视图由真实证据组装并注册为 Artifact，经
 * open_with_context 信封回到标的研究工作台（上下文不丢失）。
 */

async function openWorkspaceWith(
  sourceModule: string,
  domainType: string,
  domainId: string,
  instrumentId: string,
): Promise<string> {
  const artifact = await artifactByDomain(domainType, domainId);
  if (artifact == null) {
    throw new Error("artifact.not_found");
  }
  const envelope = await recordHandoff({
    source_module: sourceModule,
    target_module: "workspace",
    action: "open_with_context",
    artifact_ids: [artifact.artifact_id],
    context: newResearchContext({
      primary_instrument_id: instrumentId,
      instrument_ids: [instrumentId],
    }),
    message: `${sourceModule} → open_with_context`,
  });
  return handoffPath(`/instrument/${instrumentId}`, envelope);
}

function WorkspaceLinkButton({
  sourceModule,
  domainType,
  domainId,
  instrumentId,
  testid,
  label,
}: {
  sourceModule: string;
  domainType: string;
  domainId: string;
  instrumentId: string;
  testid: string;
  label: string;
}) {
  const mutation = useMutation({
    mutationFn: () => openWorkspaceWith(sourceModule, domainType, domainId, instrumentId),
    onSuccess: (path: string) => {
      window.location.assign(path);
    },
  });
  return (
    <button
      type="button"
      className="control-btn"
      data-testid={testid}
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {label}
    </button>
  );
}

interface IndustryMap {
  map_id: string;
  instrument_id: string;
  industry_label: string;
  as_of: string | null;
  industry_chain: string[];
  main_business: string | null;
  related_instruments: Array<{ instrument_id: string; name: string; code: string; basis: string }>;
  disclosures: Record<string, string>;
}

interface GlobalContext {
  snapshot_id: string;
  instrument_id: string;
  topic: string;
  as_of: string | null;
  themes: Array<{
    title: string;
    topic: string | null;
    mentions_official_body: boolean;
    official_bodies: string[];
    summary: string;
    available_time: string;
    evidence_id: string;
  }>;
  disclosures: Record<string, string>;
}

export function IndustryMapPage() {
  const params = useParams();
  const instrumentId = params.instrumentId ?? "";
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["industry-map", instrumentId],
    enabled: instrumentId !== "",
    queryFn: async (): Promise<IndustryMap> => {
      const resp = await fetch(`/api/v1/research-map/industry-map/${instrumentId}`);
      if (!resp.ok) throw new Error("industry_map.not_collected");
      const body = (await resp.json()) as { industry_map: IndustryMap };
      return body.industry_map;
    },
  });

  if (isPending) {
    return (
      <main className="page" data-testid="industry-map-page">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError || !data) {
    return (
      <main className="page" data-testid="industry-map-page">
        <p className="status-error">{t("industryMap.notReady")}</p>
        <Link to={`/instrument/${instrumentId}`} className="control-btn">
          {t("industryMap.backToWorkspace")}
        </Link>
      </main>
    );
  }

  return (
    <main className="page" data-testid="industry-map-page">
      <p>
        <Link to={`/instrument/${instrumentId}`} className="secondary">
          ← {t("workspace.open")}
        </Link>
      </p>
      <div className="watch-card-head">
        <h1>{t("industryMap.title")}</h1>
        <span className="secondary">{formatWhen(data.as_of, "zh")}</span>
      </div>
      <section className="card">
        <h2>{t("industryMap.chainTitle")}</h2>
        <p className="mono" data-testid="industry-chain">
          {data.industry_chain.join(" → ")}
        </p>
        {data.main_business && (
          <>
            <h2>{t("industryMap.mainBusiness")}</h2>
            <p>{data.main_business}</p>
          </>
        )}
      </section>
      <section className="card">
        <h2>{t("industryMap.relatedTitle")}</h2>
        {data.related_instruments.length === 0 ? (
          <p className="secondary">{t("industryMap.noRelated")}</p>
        ) : (
          <ul className="watch-list">
            {data.related_instruments.map((r) => (
              <li className="result-row" key={r.instrument_id}>
                <Link to={`/instrument/${r.instrument_id}`} className="result-name">
                  {r.name} · {r.code}
                </Link>
                <span className="secondary">{r.basis}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="secondary">{data.disclosures.note}</p>
      </section>
      <WorkspaceLinkButton
        sourceModule="industry_map"
        domainType="IndustryMapSnapshot"
        domainId={data.map_id}
        instrumentId={instrumentId}
        testid="industry-map-open-workspace"
        label={t("industryMap.openWorkspace")}
      />
    </main>
  );
}

export function GlobalContextPage() {
  const params = useParams();
  const instrumentId = params.instrumentId ?? "";
  const { t } = useTranslation();
  const { data, isPending, isError } = useQuery({
    queryKey: ["global-context", instrumentId],
    enabled: instrumentId !== "",
    queryFn: async (): Promise<GlobalContext> => {
      const resp = await fetch(`/api/v1/research-map/global-context/${instrumentId}`);
      if (!resp.ok) throw new Error("global_context.not_collected");
      const body = (await resp.json()) as { global_context: GlobalContext };
      return body.global_context;
    },
  });

  if (isPending) {
    return (
      <main className="page" data-testid="global-context-page">
        <p className="secondary">{t("common.loading")}</p>
      </main>
    );
  }
  if (isError || !data) {
    return (
      <main className="page" data-testid="global-context-page">
        <p className="status-error">{t("globalContext.notReady")}</p>
        <Link to={`/instrument/${instrumentId}`} className="control-btn">
          {t("industryMap.backToWorkspace")}
        </Link>
      </main>
    );
  }

  return (
    <main className="page" data-testid="global-context-page">
      <p>
        <Link to={`/instrument/${instrumentId}`} className="secondary">
          ← {t("workspace.open")}
        </Link>
      </p>
      <div className="watch-card-head">
        <h1>{t("globalContext.title")}</h1>
        <span className="secondary">{formatWhen(data.as_of, "zh")}</span>
      </div>
      <p className="secondary" data-testid="global-context-disclosure">
        {data.disclosures.note}
      </p>
      <section className="card">
        <h2>{t("globalContext.themesTitle")}</h2>
        <ul className="watch-list">
          {data.themes.map((theme) => (
            <li className="result-row" key={theme.evidence_id}>
              <span>{theme.title}</span>
              <span className="secondary">
                {theme.mentions_official_body ? theme.official_bodies.join("、") : ""}
              </span>
              <span className="secondary">{formatWhen(theme.available_time, "zh")}</span>
            </li>
          ))}
        </ul>
      </section>
      <WorkspaceLinkButton
        sourceModule="global_context"
        domainType="GlobalContextSnapshot"
        domainId={data.snapshot_id}
        instrumentId={instrumentId}
        testid="global-context-open-workspace"
        label={t("globalContext.openWorkspace")}
      />
    </main>
  );
}
