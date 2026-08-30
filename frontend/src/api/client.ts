/**
 * Auth-aware fetch wrapper（任务书 §34 API 层集中）。
 * 全局拦截器（main.tsx）已注入 Bearer token —— 此处提供
 * 类型化方法供页面消费，替代散落的 raw fetch。
 */
export class ApiError extends Error {
  readonly errorCode: string;
  readonly status: number;

  constructor(status: number, errorCode: string, detail?: string) {
    super(detail ?? errorCode);
    this.status = status;
    this.errorCode = errorCode;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new ApiError(resp.status, body?.error_code ?? "network.unreachable");
  }
  return resp.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok && resp.status !== 202) {
    const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new ApiError(resp.status, err?.error_code ?? "network.unreachable");
  }
  return resp.json();
}

export async function apiDelete(path: string): Promise<void> {
  const resp = await fetch(path, { method: "DELETE" });
  if (!resp.ok && resp.status !== 204) {
    const err = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new ApiError(resp.status, err?.error_code ?? "network.unreachable");
  }
}
