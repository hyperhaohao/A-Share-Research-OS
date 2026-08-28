import { useTheme } from "../theme/ThemeProvider";
import { useLanguage } from "../i18n/LanguageProvider";
import { useTranslation } from "react-i18next";
import type { ThemePreference } from "../theme/theme";
import type { LanguagePreference } from "../i18n";

/**
 * PW0 (§8/§9): appearance + language are single-select controls — one
 * <select> each, not three side-by-side buttons. ThemeProvider /
 * LanguageProvider / localStorage / prefers-color-scheme logic is unchanged.
 */
export function AppearanceControls() {
  const { t } = useTranslation();
  const { preference, setPreference } = useTheme();

  const options: Array<{ value: ThemePreference; label: string }> = [
    { value: "system", label: t("settings.appearanceSystem") },
    { value: "light", label: t("settings.appearanceLight") },
    { value: "dark", label: t("settings.appearanceDark") },
  ];

  return (
    <div role="group" aria-label={t("settings.appearance")}>
      <span className="control-label">{t("settings.appearance")}</span>
      <select
        className="control-select"
        value={preference}
        aria-label={t("settings.appearance")}
        onChange={(e) => setPreference(e.target.value as ThemePreference)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function LanguageControls() {
  const { t } = useTranslation();
  const { preference, setPreference } = useLanguage();

  const options: Array<{ value: LanguagePreference; label: string }> = [
    { value: "system", label: t("settings.languageSystem") },
    { value: "zh-CN", label: "简体中文" },
    { value: "en-US", label: "English" },
  ];

  return (
    <div role="group" aria-label={t("settings.language")}>
      <span className="control-label">{t("settings.language")}</span>
      <select
        className="control-select"
        value={preference}
        aria-label={t("settings.language")}
        onChange={(e) => setPreference(e.target.value as LanguagePreference)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
