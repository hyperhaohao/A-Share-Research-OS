/**
 * Auth-aware fetch wrapper（任务书 §34 API 层集中）：
 * 自动注入 Bearer token；401 → /login redirect。
 */
export async function authFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const token = localStorage.getItem("asro_token");
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const resp = await fetch(path, { ...init, headers });
  if (resp.status === 401 && !path.includes("/auth/")) {
    localStorage.removeItem("asro_token");
    window.location.assign("/login");
  }
  return resp;
}
