import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * 登录页（部署准备：多用户认证）。
 * ASRO_AUTH_ENABLED=false 时不会跳到此页（后端不返回 401）。
 */
export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const resp = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
        throw new Error(body?.error_code ?? "auth.invalid_credentials");
      }
      const body = (await resp.json()) as { access_token: string };
      localStorage.setItem("asro_token", body.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "auth.invalid_credentials");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="page layout-reading" data-testid="login-page">
      <h1>{t("login.title")}</h1>
      <form onSubmit={onSubmit} className="card" style={{ maxWidth: 400, margin: "0 auto", padding: "var(--space-5)" }}>
        <div className="task-grid">
          <label htmlFor="login-username">{t("login.username")}</label>
          <input
            id="login-username"
            className="control-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <label htmlFor="login-password">{t("login.password")}</label>
          <input
            id="login-password"
            type="password"
            className="control-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        {error && (
          <p className="status-error" style={{ marginTop: "var(--space-3)" }}>
            {error === "auth.invalid_credentials"
              ? t("login.invalidCredentials")
              : t(`errors.${error}`, { defaultValue: t("common.error") })}
          </p>
        )}
        <button
          type="submit"
          className="control-btn"
          data-testid="login-submit"
          disabled={pending || !username.trim() || !password}
          style={{ marginTop: "var(--space-3)", width: "100%" }}
        >
          {t("login.submit")}
        </button>
      </form>
    </main>
  );
}
