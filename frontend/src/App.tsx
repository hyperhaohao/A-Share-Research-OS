import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AppHeader } from "./components/AppHeader";
import { HomePage } from "./pages/HomePage";
import { ThemeProvider } from "./theme/ThemeProvider";
import { LanguageProvider } from "./i18n/LanguageProvider";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function Shell() {
  const { t } = useTranslation();
  return (
    <div className="app">
      <AppHeader />
      <HomePage />
      <footer className="app-footer secondary">{t("app.tagline")}</footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LanguageProvider>
          <Shell />
        </LanguageProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
