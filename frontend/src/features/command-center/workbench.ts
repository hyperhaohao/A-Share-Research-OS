/**
 * 帷幄 Dynamic Workbench API client（F8，任务书 §8.7）.
 *
 * 每会话独立 Tab 状态持久化在服务端（刷新恢复）；Tab 来自注册表白名单页面，
 * payload 驱动真实页面（route 占位符 + handoff 参数）；Artifact 自动打开
 * 由后端完成（workbench_open_requested / artifact_created 事件），前端轮询
 * 恢复 + 用户手动 open/close/activate。
 */

export interface WorkbenchTab {
  tab_id: string;
  session_id: string;
  page: string;
  title: string;
  payload: Record<string, unknown>;
  artifact_id: string | null;
  is_active: boolean;
  route: string;
  created_at: string | null;
}

export async function fetchWorkbenchTabs(sessionId: string): Promise<WorkbenchTab[]> {
  const resp = await fetch(`/api/v1/command/sessions/${sessionId}/workbench`);
  if (!resp.ok) return [];
  const body = (await resp.json()) as { tabs: WorkbenchTab[] };
  return body.tabs ?? [];
}

export async function openWorkbenchTab(
  sessionId: string,
  body: { artifact_id?: string; page?: string; payload?: Record<string, unknown> },
): Promise<WorkbenchTab | null> {
  const resp = await fetch(`/api/v1/command/sessions/${sessionId}/workbench/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) return null;
  const parsed = (await resp.json()) as { tab: WorkbenchTab };
  return parsed.tab ?? null;
}

export async function closeWorkbenchTab(sessionId: string, tabId: string): Promise<boolean> {
  const resp = await fetch(`/api/v1/command/sessions/${sessionId}/workbench/${tabId}`, {
    method: "DELETE",
  });
  return resp.ok;
}

export async function activateWorkbenchTab(sessionId: string, tabId: string): Promise<boolean> {
  const resp = await fetch(
    `/api/v1/command/sessions/${sessionId}/workbench/${tabId}/activate`,
    { method: "POST" },
  );
  return resp.ok;
}

/** payload 驱动真实路由：替换 {report_id} 等占位符 + 携带 artifact 溯源参数。 */
export function resolveTabRoute(tab: WorkbenchTab): string {
  let route = tab.route || "/";
  for (const [key, value] of Object.entries(tab.payload ?? {})) {
    if (typeof value === "string" || typeof value === "number") {
      route = route.replaceAll(`{${key}}`, String(value));
    }
  }
  const params = new URLSearchParams();
  if (tab.artifact_id) params.set("artifact_id", tab.artifact_id);
  const instrumentId = tab.payload?.instrument_ids;
  if (Array.isArray(instrumentId) && instrumentId.length > 0) {
    params.set("instrument", String(instrumentId[0]));
  }
  const query = params.toString();
  if (query) route += (route.includes("?") ? "&" : "?") + query;
  return route;
}
