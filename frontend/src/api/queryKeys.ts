/** Query Key Factory（任务书 §34）。 */
export const queryKeys = {
  instrument: (id: string) => ["instrument", id],
  watchlistView: () => ["watchlist-view"],
  reportLibrary: () => ["report-library"],
  commandCenter: () => ["command-center-view"],
  continuousResearch: () => ["continuous-research-view"],
  predictionReview: () => ["prediction-review-view"],
  experienceCards: () => ["experience-cards-view"],
  workflowRuns: (cardId?: string) => ["workflow-runs", cardId],
  screeningRuns: () => ["screening-runs"],
  strategies: () => ["strategies"],
  monitors: () => ["strategy-monitors"],
  researchGraph: () => ["research-graph"],
  sourceHealth: () => ["source-health"],
};
