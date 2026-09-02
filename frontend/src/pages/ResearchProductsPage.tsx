/**
 * G9 — Research Products 页面（任务书 §G9）：
 * 三市场级产品（主线雷达/海外证据雷达/研究晨报）的版本化编译入口 +
 * Artifact/Version/PIT 显形 + 条目链接。
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Badge, Panel } from "../ui/guanlan";

interface CompileResult {
  compile_id: string;
  product_type: string;
  version: number;
  as_of: string | null;
  artifact_id: string | null;
  provenance_status: string;
  product: {
    items?: Array<{ evidence_id?: string; title?: string; text?: string }>;
    sections?: Array<{ title: string; items: Array<{ text?: string }> }>;
    missing_chain?: string[];
  };
  diff_vs_previous: {
    version: number;
    previous_version: number | null;
    changed?: boolean | null;
  };
}

const PRODUCTS = [
  { kind: "mainline-radar", labelKey: "researchProducts.mainline", type: "MAINLINE_RADAR" },
  { kind: "overseas-mapping", labelKey: "researchProducts.overseas", type: "OVERSEAS_EVIDENCE_RADAR" },
  { kind: "daily-brief", labelKey: "researchProducts.dailyBrief", type: "DAILY_RESEARCH_BRIEF" },
];

async function compileProduct(kind: string): Promise<CompileResult> {
  const resp = await fetch(`/api/v1/research-products/${kind}/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  if (!resp.ok) throw new Error("compile.failed");
  return resp.json();
}

export function ResearchProductsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [results, setResults] = useState<Record<string, CompileResult>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const compileMutation = useMutation({
    mutationFn: compileProduct,
    onSuccess: (data) => {
      setResults((prev) => ({ ...prev, [data.product_type]: data }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[data.product_type];
        return next;
      });
      void qc.invalidateQueries({ queryKey: ["rp-compiles"] });
    },
    onError: () => setErrors((prev) => ({ ...prev })),
  });

  const compilesQuery = useQuery({
    queryKey: ["rp-compiles"],
    queryFn: async () => {
      const resp = await fetch("/api/v1/research-products/compiles");
      if (!resp.ok) return { results: [] as Array<Record<string, unknown>> };
      return resp.json();
    },
  });

  return (
    <main className="page" data-testid="research-products-page">
      <h1>{t("researchProducts.title")}</h1>
      <p className="secondary">{t("researchProducts.subtitle")}</p>
      <div className="rc-grid">
        {PRODUCTS.map((p) => {
          const result = results[p.type];
          const err = errors[p.type];
          return (
            <Panel key={p.kind} title={t(p.labelKey)}>
              <button
                type="button"
                className="gl-button gl-button-primary"
                data-testid={`compile-${p.kind}`}
                disabled={compileMutation.isPending}
                onClick={() =>
                  compileMutation.mutate(p.kind, {
                    onError: () =>
                      setErrors((prev) => ({ ...prev, [p.type]: t("researchProducts.compileFailed") })),
                  })
                }
              >
                {t("researchProducts.compile")}
              </button>
              {result && (
                <div className="rp-result" data-testid={`rp-result-${p.kind}`}>
                  <p className="secondary mono">
                    v{result.version} · {result.as_of?.slice(0, 19)} ·{" "}
                    {result.artifact_id?.slice(0, 14)}
                  </p>
                  <Badge tone={result.provenance_status === "complete" ? "ok" : "warning"}>
                    {result.provenance_status}
                  </Badge>
                  {result.product.missing_chain && result.product.missing_chain.length > 0 && (
                    <p className="secondary status-error">
                      {t("researchProducts.missingChain")}: {result.product.missing_chain.join(", ")}
                    </p>
                  )}
                  {result.diff_vs_previous.previous_version != null && (
                    <p className="secondary">
                      {t("researchProducts.diffVsPrevious")}: v
                      {result.diff_vs_previous.previous_version} → v{result.diff_vs_previous.version} ·{" "}
                      {result.diff_vs_previous.changed
                        ? t("researchProducts.changed")
                        : t("researchProducts.unchanged")}
                    </p>
                  )}
                </div>
              )}
              {err && <p className="status-error">{err}</p>}
            </Panel>
          );
        })}
      </div>

      <Panel title={t("researchProducts.versionHistory")}>
        <ul className="watch-list" data-testid="rp-compiles">
          {((compilesQuery.data?.results ?? []) as Array<Record<string, unknown>>).map((c, i) => (
            <li key={String(c.compile_id ?? i)} className="result-row">
              <span className="mono">{String(c.product_type)}</span>
              <span className="secondary mono">v{String(c.version)}</span>
              <span className="secondary mono">{String(c.as_of ?? "").slice(0, 19)}</span>
              <Badge tone={c.provenance_status === "complete" ? "ok" : "warning"}>
                {String(c.provenance_status)}
              </Badge>
            </li>
          ))}
        </ul>
      </Panel>
    </main>
  );
}
