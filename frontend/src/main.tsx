import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

// P0-01: global fetch interceptor — inject Bearer token into all /api/v1/* calls
const _origFetch = window.fetch;
window.fetch = async function (input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (url.includes("/api/v1/") && !url.includes("/auth/")) {
    const token = localStorage.getItem("asro_token");
    if (token) {
      const headers = new Headers(init?.headers);
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return _origFetch(input, { ...init, headers });
    }
  }
  return _origFetch(input, init);
};
import "./i18n";
import "./styles/tokens.css";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
