import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
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
import { IndustryResearchWorkspace } from "./features/industry-research/IndustryResearchWorkspace";
import { GlobalMacroWorkspace } from "./features/global-macro/GlobalMacroWorkspace";
import { ResearchInboxPage, ResearchMemoryPage, ThesisCenterPage } from "./features/research-center/ResearchCenterPages";
import { ResearchGraphPage } from "./pages/ResearchGraphPage";
import { ResearchGraphCanvasPage } from "./pages/ResearchGraphCanvas";
import { ThemeProvider } from "./theme/ThemeProvider";
import { LanguageProvider } from "./i18n/LanguageProvider";
import { AppShell } from "./app/AppShell";
import { WithInstrumentRedirect } from "./app/InstrumentRedirect";
import { ResearchProductsPage } from "./pages/ResearchProductsPage";
import { WorkflowsPage, WorkflowDetailPage } from "./pages/WorkflowsPage";
import { WorkflowStudioPage } from "./pages/WorkflowStudioPage";
import { SourceHealthPage } from "./pages/SourceHealthPage";
import { LoginPage } from "./pages/LoginPage";
import { Navigate } from "react-router-dom";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

// 导航由 app/navigation.ts 分组 Sidebar 承载（任务书 §5）

function Shell() {
  const { t } = useTranslation();
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/predictions" element={<PredictionsPage />} />
        <Route path="/experience" element={<ExperienceCardsPage />} />
        <Route path="/experience/:cardId" element={<ExperienceCardPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/:runId" element={<WorkflowDetailPage />} />
        <Route path="/workflow-studio" element={<WorkflowStudioPage />} />
        <Route path="/screening" element={<ScreeningRunsPage />} />
        <Route path="/screening/:runId" element={<ScreeningRunDetailPage />} />
        <Route path="/strategy" element={<StrategyLabPage />} />
        <Route path="/strategy/:versionId" element={<StrategyDetailPage />} />
        <Route path="/monitoring" element={<StrategyMonitorsPage />} />
        <Route path="/monitoring/:monitorId" element={<StrategyMonitorDetailPage />} />
        <Route
          path="/industry-map"
          element={
            <WithInstrumentRedirect basePath="/industry-map">
              {() => <IndustryResearchWorkspace initialTab="chain" />}
            </WithInstrumentRedirect>
          }
        />
        <Route path="/industry-map/:instrumentId" element={<IndustryResearchWorkspace initialTab="chain" />} />
        <Route
          path="/global-context"
          element={
            <WithInstrumentRedirect basePath="/global-context">
              {() => <IndustryResearchWorkspace initialTab="global" />}
            </WithInstrumentRedirect>
          }
        />
        <Route path="/global-context/:instrumentId" element={<IndustryResearchWorkspace initialTab="global" />} />
        <Route path="/global-macro" element={<GlobalMacroWorkspace />} />
        <Route path="/research-inbox" element={<ResearchInboxPage />} />
        <Route path="/research-memory" element={<ResearchMemoryPage />} />
        <Route path="/thesis-center" element={<ThesisCenterPage />} />
        <Route path="/research-products" element={<ResearchProductsPage />} />
        <Route path="/research-graph" element={<ResearchGraphCanvasPage />} />
        <Route path="/research-graph/list" element={<ResearchGraphPage />} />
        <Route path="/source-health" element={<SourceHealthPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:reportId" element={<InteractiveReportPage />} />
        <Route path="/instrument/:instrumentId" element={<InstrumentWorkspacePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <footer className="app-footer secondary">{t("app.tagline")}</footer>
    </AppShell>
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
