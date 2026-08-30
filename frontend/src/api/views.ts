/** UI Read Model API — typed wrappers for /views/* endpoints. */
import { apiGet } from "./client";

export interface WatchCardView {
  instrument_id: string;
  instrument: { instrument_id: string; name: string | null; code: string; exchange: string; board: string } | null;
  quote: { price: number; change_pct: number | null; quote_time: string | null } | null;
  research: { judgment: string | null; confidence: number | null; thesis_title: string | null; support_balance: string | null };
  report: { report_id: string; created_at: string | null } | null;
  prediction: Record<string, unknown> | null;
  monitor: Record<string, unknown> | null;
  added_at: string | null;
}

export function fetchWatchlistView(): Promise<{ count: number; results: WatchCardView[] }> {
  return apiGet("/api/v1/views/watchlist");
}

export interface OverviewView {
  instrument: Record<string, unknown> | null;
  quote: { price: number; change_pct: number | null } | null;
  research: Record<string, unknown>;
  catalysts: string[];
  risks: string[];
  report: { report_id: string; created_at: string | null } | null;
  prediction: Record<string, unknown> | null;
  monitor: Record<string, unknown> | null;
  valuation: Record<string, unknown> | null;
  latest_changes: Array<{ evidence_type: string; title: string; available_time: string }>;
  data_quality: { evidence_count: number; source_kinds: number; quality_score: string; capability_breakdown: Record<string, number> };
}

export function fetchInstrumentOverview(id: string): Promise<{ overview: OverviewView }> {
  return apiGet(`/api/v1/views/instruments/${encodeURIComponent(id)}/overview`);
}

export function fetchCommandCenter(): Promise<{ view: Record<string, unknown> }> {
  return apiGet("/api/v1/views/command-center");
}

export function fetchReportLibrary(): Promise<{ count: number; results: Array<Record<string, unknown>> }> {
  return apiGet("/api/v1/views/report-library");
}

export function fetchContinuousResearch(): Promise<{ count: number; results: Array<Record<string, unknown>> }> {
  return apiGet("/api/v1/views/continuous-research");
}

export function fetchPredictionReview(): Promise<{ count: number; results: Array<Record<string, unknown>>; kpi: Record<string, unknown>; generated_at: string | null }> {
  return apiGet("/api/v1/views/prediction-review");
}

export function fetchExperienceCards(): Promise<{ count: number; results: Array<Record<string, unknown>> }> {
  return apiGet("/api/v1/views/experience-cards");
}
