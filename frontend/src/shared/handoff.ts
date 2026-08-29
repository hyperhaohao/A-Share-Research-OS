/**
 * HandoffEnvelope — 跨模块动作的唯一通道（V2 Phase A, HANDOFF-PROTOCOL §2/§4）。
 *
 * 页面只消费这里：构造信封（POST /handoffs，未注册动作服务端 422 显形）
 * + 解析 artifact（GET /artifacts/by-domain/...）+ 携带 handoff/context 的
 * 跳转 URL。页面不自行拼跨模块上下文（红线 5）。
 */

import { newResearchContext, type ContextSeed, type ResearchContext } from "./context";

export interface Artifact {
  artifact_id: string;
  artifact_type: string;
  domain_type: string;
  domain_id: string;
  title: string;
  instrument_ids: string[];
  route: string;
  version: number | null;
}

export interface HandoffEnvelope {
  handoff_id: string;
  source_module: string;
  target_module: string;
  action: string;
  artifact_ids: string[];
  context: ResearchContext;
  message: string | null;
  created_at: string;
}

export class HandoffRefused extends Error {
  readonly errorCode: string;
  constructor(errorCode: string, detail: string) {
    super(detail);
    this.errorCode = errorCode;
  }
}

/** 域对象 → registry artifact（例：Report rpt_xxx → art_xxx）。 */
export async function artifactByDomain(
  domainType: string,
  domainId: string,
): Promise<Artifact | null> {
  const resp = await fetch(
    `/api/v1/artifacts/by-domain/${encodeURIComponent(domainType)}/${encodeURIComponent(domainId)}`,
  );
  if (resp.status === 404) return null;
  if (!resp.ok) throw new HandoffRefused("network.unreachable", `HTTP ${resp.status}`);
  const body = (await resp.json()) as { artifact: Artifact };
  return body.artifact;
}

export interface HandoffInput {
  source_module: string;
  target_module: string;
  action: string;
  artifact_ids: string[];
  context?: ResearchContext;
  context_seed?: ContextSeed;
  message?: string;
}

/** 记录一次跨模块动作；服务端校验动作注册表 + artifact 存在性。 */
export async function recordHandoff(input: HandoffInput): Promise<HandoffEnvelope> {
  const context = input.context ?? newResearchContext(input.context_seed ?? {});
  const resp = await fetch("/api/v1/handoffs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_module: input.source_module,
      target_module: input.target_module,
      action: input.action,
      artifact_ids: input.artifact_ids,
      context,
      message: input.message ?? null,
    }),
  });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as
      | { error_code?: string; detail?: string }
      | null;
    throw new HandoffRefused(body?.error_code ?? "network.unreachable", body?.detail ?? `HTTP ${resp.status}`);
  }
  const body = (await resp.json()) as { handoff: HandoffEnvelope };
  return body.handoff;
}

/** 跳转 URL：目标页路径 + handoff/context 溯源参数。 */
export function handoffPath(path: string, envelope: HandoffEnvelope): string {
  const params = new URLSearchParams({
    handoff: envelope.handoff_id,
    context: envelope.context.context_id,
  });
  return `${path}?${params.toString()}`;
}
