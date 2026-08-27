import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AppHeader } from "./components/AppHeader";
import { HomePage } from "./pages/HomePage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { ReportsPage } from "./pages/ReportsPage";
import { InteractiveReportPage } from "./pages/InteractiveReportPage";
import { InstrumentWorkspacePage } from "./pages/InstrumentWorkspacePage";
import { ThemeProvider } from "./theme/ThemeProvider";
import { LanguageProvider } from "./i18n/LanguageProvider";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const NAV_ITEMS: Array<{ to: string; key: string }> = [
  { to: "/", key: "nav.dashboard" },
  { to: "/watchlist", key: "nav.watchlist" },
  { to: "/reports", key: "nav.reports" },
];

function Shell() {
  const { t } = useTranslation();
  return (
    <div className="app">
      <AppHeader />
      <nav className="app-nav" aria-label={t("nav.dashboard")}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {t(item.key)}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:reportId" element={<InteractiveReportPage />} />
        <Route path="/instrument/:instrumentId" element={<InstrumentWorkspacePage />} />
      </Routes>
      <footer className="app-footer secondary">{t("app.tagline")}</footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <LanguageProvider>
            <Shell />
          </LanguageProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
