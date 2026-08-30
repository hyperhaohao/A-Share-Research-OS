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
      { to: "/", labelKey: "nav.commander" },
      { to: "/watchlist", labelKey: "nav.company" },
      { to: "/reports", labelKey: "nav.reports" },
      { to: "/industry-map", labelKey: "nav.industryMap" },
      { to: "/global-context", labelKey: "nav.industryGlobal" },
      { to: "/global-macro", labelKey: "nav.globalMacro" },
      { to: "/experience", labelKey: "nav.experience" },
      { to: "/tasks", labelKey: "nav.tasks" },
      { to: "/research-graph", labelKey: "nav.researchGraph" },
    ],
  },
  {
    // 实验分组（ADR-Research-First）：量化面保留但冻结，降为 Experimental
    key: "experimental",
    labelKey: "nav.group.experimental",
    items: [
      { to: "/screening", labelKey: "nav.screening" },
      { to: "/workflows", labelKey: "nav.workflows" },
      { to: "/workflow-studio", labelKey: "nav.workflowStudio" },
      { to: "/strategy", labelKey: "nav.strategy" },
      { to: "/monitoring", labelKey: "nav.monitoring" },
      { to: "/predictions", labelKey: "nav.predictions" },
    ],
  },
]
