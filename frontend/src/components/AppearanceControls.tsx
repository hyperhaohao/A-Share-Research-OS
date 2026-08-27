import { useTheme } from "../theme/ThemeProvider";
import { useLanguage } from "../i18n/LanguageProvider";
import { useTranslation } from "react-i18next";
import type { ThemePreference } from "../theme/theme";
import type { LanguagePreference } from "../i18n";

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
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={preference === opt.value ? "control-btn active" : "control-btn"}
          aria-pressed={preference === opt.value}
          onClick={() => setPreference(opt.value)}
        >
          {opt.label}
        </button>
      ))}
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
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={preference === opt.value ? "control-btn active" : "control-btn"}
          aria-pressed={preference === opt.value}
          onClick={() => setPreference(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
