import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AppHeader } from "./components/AppHeader";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HomePage } from "./pages/HomePage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { ReportsPage } from "./pages/ReportsPage";
import { InteractiveReportPage } from "./pages/InteractiveReportPage";
import { InstrumentWorkspacePage } from "./pages/InstrumentWorkspacePage";
import { TasksPage } from "./pages/TasksPage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { ExperienceCardsPage } from "./pages/ExperienceCardsPage";
import { ExperienceCardPage } from "./pages/ExperienceCardPage";
import { ScreeningRunsPage, ScreeningRunDetailPage } from "./pages/ScreeningPage";
import { StrategyLabPage, StrategyDetailPage } from "./pages/StrategyLabPage";
import { StrategyMonitorsPage, StrategyMonitorDetailPage } from "./pages/StrategyMonitorPage";
import { IndustryMapPage, GlobalContextPage } from "./pages/ResearchMapPages";
import { ResearchGraphPage } from "./pages/ResearchGraphPage";
import { ThemeProvider } from "./theme/ThemeProvider";
import { LanguageProvider } from "./i18n/LanguageProvider";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const NAV_ITEMS: Array<{ to: string; key: string }> = [
  { to: "/", key: "nav.dashboard" },
  { to: "/watchlist", key: "nav.watchlist" },
  { to: "/tasks", key: "nav.tasks" },
  { to: "/predictions", key: "nav.predictions" },
  { to: "/experience", key: "nav.experience" },
  { to: "/screening", key: "nav.screening" },
  { to: "/strategy", key: "nav.strategy" },
  { to: "/monitoring", key: "nav.monitoring" },
  { to: "/research-graph", key: "nav.researchGraph" },
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
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/predictions" element={<PredictionsPage />} />
        <Route path="/experience" element={<ExperienceCardsPage />} />
        <Route path="/experience/:cardId" element={<ExperienceCardPage />} />
        <Route path="/screening" element={<ScreeningRunsPage />} />
        <Route path="/screening/:runId" element={<ScreeningRunDetailPage />} />
        <Route path="/strategy" element={<StrategyLabPage />} />
        <Route path="/strategy/:versionId" element={<StrategyDetailPage />} />
        <Route path="/monitoring" element={<StrategyMonitorsPage />} />
        <Route path="/monitoring/:monitorId" element={<StrategyMonitorDetailPage />} />
        <Route path="/industry-map/:instrumentId" element={<IndustryMapPage />} />
        <Route path="/global-context/:instrumentId" element={<GlobalContextPage />} />
        <Route path="/research-graph" element={<ResearchGraphPage />} />
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
            <ErrorBoundary>
              <Shell />
            </ErrorBoundary>
          </LanguageProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
