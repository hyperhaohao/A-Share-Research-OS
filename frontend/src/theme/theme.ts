/**
 * Theme resolution — pure, testable logic.
 *
 * Three-state appearance (task书 §12-13):
 *   system  — follow OS prefers-color-scheme (default)
 *   light   — force light
 *   dark    — force dark
 *
 * Applied via `data-theme` attribute on <html>. Colors themselves live in
 * styles/tokens.css as CSS variables (task书 §14).
 */

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "asro.appearance";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme {
  if (preference === "system") return systemPrefersDark ? "dark" : "light";
  return preference;
}

export function applyTheme(theme: ResolvedTheme): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", theme);
}

/**
 * Apply resolved theme and (un)subscribe the OS listener.
 * Returns a cleanup function for the OS listener.
 *
 * Semantics required by task书 §77:
 *  - preference = system → follow OS changes live;
 *  - manual light/dark → NOT overridden by OS changes.
 */
export function bindTheme(
  preference: ThemePreference,
  onChange: (theme: ResolvedTheme) => void,
): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => undefined;

  const mql = window.matchMedia("(prefers-color-scheme: dark)");
  const sync = () => onChange(resolveTheme(preference, mql.matches));
  sync();

  if (preference === "system") {
    mql.addEventListener("change", sync);
    return () => mql.removeEventListener("change", sync);
  }
  return () => undefined;
}
