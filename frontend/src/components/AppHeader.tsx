import { useTranslation } from "react-i18next";
import { AppearanceControls, LanguageControls } from "./AppearanceControls";

export function AppHeader() {
  const { t } = useTranslation();
  return (
    <header className="app-header">
      <div>
        <span className="app-title">{t("app.title")}</span>
        <span className="app-tagline secondary">{t("app.tagline")}</span>
      </div>
      <div className="header-controls">
        <AppearanceControls />
        <LanguageControls />
      </div>
    </header>
  );
}
