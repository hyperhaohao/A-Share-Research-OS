/**
 * ResearchContext — URL 编解码的唯一入口（V2 Phase A, HANDOFF-PROTOCOL §1/§4）。
 *
 * 页面不自行拼上下文：构造走 newResearchContext，进出 URL 走
 * contextToParams / contextFromParams。Context 只描述当前研究上下文，
 * 不是业务真数据（红线 4/5：业务物料永远后端持久化）。
 */

export interface ResearchContext {
  context_id: string;
  instrument_ids: string[];
  primary_instrument_id: string | null;
  /** ISO datetime；进入任何 Run 前必须落值（PIT） */
  as_of_time: string | null;
  snapshot_id: string | null;
  research_run_id: string | null;
  report_version_id: string | null;
  selected_artifact_ids: string[];
  locale: string;
  created_at: string;
}

export type ContextSeed = Partial<Omit<ResearchContext, "context_id" | "created_at">>;

function hex12(): string {
  const buf = new Uint8Array(6);
  crypto.getRandomValues(buf);
  return Array.from(buf, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** 不可变：任何字段变更都生成新的 context_id。 */
export function newResearchContext(seed: ContextSeed = {}): ResearchContext {
  return {
    context_id: `ctx_${hex12()}`,
    instrument_ids: seed.instrument_ids ?? [],
    primary_instrument_id: seed.primary_instrument_id ?? null,
    as_of_time: seed.as_of_time ?? null,
    snapshot_id: seed.snapshot_id ?? null,
    research_run_id: seed.research_run_id ?? null,
    report_version_id: seed.report_version_id ?? null,
    selected_artifact_ids: seed.selected_artifact_ids ?? [],
    locale: seed.locale ?? (document.documentElement.lang || "zh-CN"),
    created_at: new Date().toISOString(),
  };
}

/**
 * Context → URL query（现有 `?instrument=SZSE:000831&run=1` 的推广）。
 * 只携带非空字段；primary instrument 映射到 `instrument`（老链接兼容）。
 */
export function contextToParams(ctx: ResearchContext, { run = false } = {}): URLSearchParams {
  const params = new URLSearchParams();
  if (ctx.primary_instrument_id) params.set("instrument", ctx.primary_instrument_id);
  if (run) params.set("run", "1");
  params.set("context", ctx.context_id);
  if (ctx.snapshot_id) params.set("snapshot", ctx.snapshot_id);
  if (ctx.research_run_id) params.set("run_id", ctx.research_run_id);
  if (ctx.report_version_id) params.set("version", ctx.report_version_id);
  return params;
}

/** URL query → Context（缺 context_id 时视为新上下文，现场铸造）。 */
export function contextFromParams(params: URLSearchParams): ResearchContext {
  const primary = params.get("instrument");
  const instrumentIds = primary ? [primary] : [];
  const runId = params.get("run_id");
  const snapshotId = params.get("snapshot");
  const versionId = params.get("version");
  const ctx = newResearchContext({
    primary_instrument_id: primary,
    instrument_ids: instrumentIds,
    research_run_id: runId,
    snapshot_id: snapshotId,
    report_version_id: versionId,
  });
  // 老链接没有 context 参数：携带过来的 id 保持原值，context_id 现场铸造
  const fromUrl = params.get("context");
  if (fromUrl) ctx.context_id = fromUrl;
  return ctx;
}

/** 拼接路径 + Context 参数（页面唯一允许的跳转构造方式）。 */
export function contextPath(path: string, ctx: ResearchContext, { run = false } = {}): string {
  const params = contextToParams(ctx, { run });
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}
