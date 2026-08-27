/**
 * i18n — first-class capability from M1 (task书 §6-8).
 *
 * Language preference: system | zh-CN | en-US.
 *  - system: zh* → zh-CN, anything else → en-US (task书 §8)
 *  - manual override persisted to localStorage (UI preference, not research fact)
 */

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import zhCN from "./locales/zh-CN.json";
import enUS from "./locales/en-US.json";

export const LANGUAGE_STORAGE_KEY = "asro.language";

export type Language = "zh-CN" | "en-US";
export type LanguagePreference = "system" | Language;

export const SUPPORTED_LANGUAGES: Array<{ code: Language; label: string }> = [
  { code: "zh-CN", label: "简体中文" },
  { code: "en-US", label: "English" },
];

export function isLanguage(value: unknown): value is Language {
  return value === "zh-CN" || value === "en-US";
}

export function isLanguagePreference(value: unknown): value is LanguagePreference {
  return value === "system" || isLanguage(value);
}

/** Pure resolution of the system language (task书 §8: zh* → zh-CN, else en-US). */
export function systemLanguage(navigatorLanguage: string): Language {
  return navigatorLanguage.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

export function resolveLanguage(
  preference: LanguagePreference,
  navigatorLanguage: string,
): Language {
  return preference === "system" ? systemLanguage(navigatorLanguage) : preference;
}

export function readStoredPreference(): LanguagePreference {
  if (typeof window === "undefined") return "system";
  const raw = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isLanguagePreference(raw) ? raw : "system";
}

export function storePreference(preference: LanguagePreference): void {
  if (typeof window === "undefined") return;
  if (preference === "system") window.localStorage.removeItem(LANGUAGE_STORAGE_KEY);
  else window.localStorage.setItem(LANGUAGE_STORAGE_KEY, preference);
}

export function browserLanguage(): string {
  if (typeof navigator === "undefined") return "en-US";
  return navigator.language || "en-US";
}

export function applyDocumentLanguage(language: Language): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("lang", language);
}

void i18n.use(initReactI18next).init({
  resources: {
    "zh-CN": { translation: zhCN },
    "en-US": { translation: enUS },
  },
  lng: resolveLanguage(readStoredPreference(), browserLanguage()),
  fallbackLng: "en-US",
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
