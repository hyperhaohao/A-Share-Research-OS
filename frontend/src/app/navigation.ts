/**
 * 分组导航（任务书 §5）：左侧 Sidebar 唯一导航源。
 * 分组：中枢 / 研究 / 验证 / 策略 / 知识 / 系统 —— 禁止继续横向追加。
 */

export interface NavItem {
  to: string;
  labelKey: string;
}

export interface NavGroup {
  key: string;
  labelKey: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    key: "research",
    labelKey: "nav.group.research",
    items: [
      { to: "/watchlist", labelKey: "nav.watchlist" },
      { to: "/reports", labelKey: "nav.reports" },
      { to: "/industry-map", labelKey: "nav.industryMap" },
      { to: "/global-context", labelKey: "nav.industryGlobal" },
      { to: "/global-macro", labelKey: "nav.globalMacro" },
    ],
  },
  {
    key: "validation",
    labelKey: "nav.group.validation",
    items: [
      { to: "/experience", labelKey: "nav.experience" },
      { to: "/workflows", labelKey: "nav.workflows" },
      { to: "/screening", labelKey: "nav.screening" },
      { to: "/workflow-studio", labelKey: "nav.workflows" },
    ],
  },
  {
    key: "strategy",
    labelKey: "nav.group.strategy",
    items: [
      { to: "/strategy", labelKey: "nav.strategy" },
      { to: "/monitoring", labelKey: "nav.monitoring" },
      { to: "/predictions", labelKey: "nav.predictions" },
    ],
  },
  {
    key: "knowledge",
    labelKey: "nav.group.knowledge",
    items: [{ to: "/research-graph", labelKey: "nav.researchGraph" }],
  },
  {
    key: "system",
    labelKey: "nav.group.system",
    items: [
      { to: "/tasks", labelKey: "nav.tasks" },
      { to: "/source-health", labelKey: "nav.sourceHealth" },
    ],
  },
];
