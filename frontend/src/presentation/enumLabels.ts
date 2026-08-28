/**
 * Presentation layer (PW0): business labels for backend enums.
 *
 * The backend keeps stable English enum values on the wire; the UI never
 * shows raw codes (SZSE / main_board / market_data / monitor / PASS …) in
 * user-facing surfaces — every value maps through here, per UI language.
 */

export type UiLanguage = "zh" | "en";

export const EXCHANGE_LABELS: Record<string, { zh: string; en: string }> = {
  SSE: { zh: "上交所", en: "Shanghai Stock Exchange" },
  SZSE: { zh: "深交所", en: "Shenzhen Stock Exchange" },
  BSE: { zh: "北交所", en: "Beijing Stock Exchange" },
};

export const BOARD_LABELS: Record<string, { zh: string; en: string }> = {
  main_board: { zh: "主板", en: "Main Board" },
  chinext: { zh: "创业板", en: "ChiNext" },
  star_market: { zh: "科创板", en: "STAR Market" },
  bse: { zh: "北交所", en: "Beijing Stock Exchange" },
};

/** Data collection capabilities (research pipeline stages). */
export const CAPABILITY_LABELS: Record<string, { zh: string; en: string }> = {
  market_data: { zh: "实时行情", en: "Realtime quote" },
  announcements: { zh: "公司公告", en: "Announcements" },
  financials: { zh: "财务数据", en: "Financials" },
  news: { zh: "新闻资讯", en: "News" },
  capital_flow: { zh: "资金流", en: "Capital flow" },
  industry: { zh: "行业数据", en: "Industry" },
  historical_data: { zh: "历史行情", en: "Historical data" },
  macro_policy: { zh: "宏观政策", en: "Macro policy" },
};

/** Analyst set (research pipeline analysis stage). */
export const ANALYST_LABELS: Record<string, { zh: string; en: string }> = {
  industry: { zh: "行业分析", en: "Industry analysis" },
  financial: { zh: "财务分析", en: "Financial analysis" },
  event: { zh: "公司事件分析", en: "Corporate event analysis" },
  news: { zh: "新闻分析", en: "News analysis" },
  capital_flow: { zh: "资金流分析", en: "Capital flow analysis" },
  macro_policy: { zh: "宏观政策分析", en: "Macro policy analysis" },
  market: { zh: "市场分析", en: "Market analysis" },
  quant: { zh: "量化分析", en: "Quant analysis" },
};

export const TASK_TYPE_LABELS: Record<string, { zh: string; en: string }> = {
  monitor: { zh: "持续研究", en: "Continuous research" },
  periodic_full_research: { zh: "定期完整研究", en: "Periodic full research" },
  event_trigger: { zh: "事件触发研究", en: "Event-triggered research" },
  prediction_validation: { zh: "预测验证", en: "Prediction validation" },
};

export const TASK_STATUS_LABELS: Record<string, { zh: string; en: string }> = {
  idle: { zh: "运行正常", en: "Healthy" },
  running: { zh: "运行中", en: "Running" },
  failed: { zh: "执行失败", en: "Failed" },
  disabled: { zh: "已暂停", en: "Paused" },
};

export const GATE_LABELS: Record<string, { zh: string; en: string }> = {
  pass: { zh: "通过", en: "Pass" },
  warn: { zh: "有警告", en: "Warning" },
  fail: { zh: "未通过", en: "Fail" },
  not_run: { zh: "未执行", en: "Not run" },
};

export const MATERIALITY_LABELS: Record<string, { zh: string; en: string }> = {
  NO_MATERIAL_CHANGE: { zh: "无重要变化", en: "No material change" },
  DELTA_RESEARCH: { zh: "发现重要变化，已增量研究", en: "Material change — delta research" },
  FULL_RESEARCH: { zh: "触发完整重研", en: "Full research triggered" },
};

export const DIRECTION_LABELS: Record<string, { zh: string; en: string }> = {
  up: { zh: "看多", en: "Bullish" },
  down: { zh: "看跌", en: "Bearish" },
  neutral: { zh: "中性", en: "Neutral" },
};

export const HORIZON_LABELS: Record<string, { zh: string; en: string }> = {
  "5D": { zh: "5个交易日", en: "5 trading days" },
  "20D": { zh: "20个交易日", en: "20 trading days" },
  "60D": { zh: "60个交易日", en: "60 trading days" },
};

/** Task schedule → business text ("每天 08:30"). */
export const SCHEDULE_LABELS: Record<string, { zh: string; en: string }> = {
  daily: { zh: "每天", en: "Daily" },
  weekdays: { zh: "工作日", en: "Weekdays" },
  weekly: { zh: "每周", en: "Weekly" },
  interval: { zh: "固定间隔", en: "Fixed interval" },
};

const DOW_LABELS: Record<string, { zh: string; en: string }> = {
  MON: { zh: "周一", en: "Monday" },
  TUE: { zh: "周二", en: "Tuesday" },
  WED: { zh: "周三", en: "Wednesday" },
  THU: { zh: "周四", en: "Thursday" },
  FRI: { zh: "周五", en: "Friday" },
  SAT: { zh: "周六", en: "Saturday" },
  SUN: { zh: "周日", en: "Sunday" },
};

type LabelTriple = { zh: string; en: string };

function lookup(
  table: Record<string, LabelTriple>,
  value: string | null | undefined,
  lang: UiLanguage,
): string {
  if (!value) return "";
  const entry = table[value];
  if (!entry) return value; // unknown value: show as-is, never invent
  return lang === "zh" ? entry.zh : entry.en;
}

export function formatExchange(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(EXCHANGE_LABELS, value, lang);
}

export function formatBoard(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(BOARD_LABELS, value, lang);
}

export function formatCapability(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(CAPABILITY_LABELS, value, lang);
}

export function formatAnalyst(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(ANALYST_LABELS, value, lang);
}

export function formatTaskType(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(TASK_TYPE_LABELS, value, lang);
}

export function formatTaskStatus(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(TASK_STATUS_LABELS, value, lang);
}

export function formatGate(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(GATE_LABELS, value, lang);
}

export function formatMateriality(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(MATERIALITY_LABELS, value, lang);
}

export function formatDirection(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(DIRECTION_LABELS, value, lang);
}

export function formatHorizon(value: string | null | undefined, lang: UiLanguage): string {
  return lookup(HORIZON_LABELS, value, lang);
}

/** "daily:08:30" → 每天 08:30 / Daily 08:30; "weekly:MON:09:00" → 每周一 09:00. */
export function formatSchedule(schedule: string | null | undefined, lang: UiLanguage): string {
  if (!schedule) return "";
  const parts = schedule.split(":");
  if (parts[0] === "interval" && parts.length === 2) {
    const seconds = Number(parts[1]);
    if (!Number.isFinite(seconds)) return schedule;
    const label = SCHEDULE_LABELS.interval[lang];
    if (seconds % 86400 === 0) return `${label} ${seconds / 86400} ${lang === "zh" ? "天" : "day(s)"}`;
    if (seconds % 3600 === 0) return `${label} ${seconds / 3600} ${lang === "zh" ? "小时" : "hour(s)"}`;
    return `${label} ${seconds} ${lang === "zh" ? "秒" : "s"}`;
  }
  if (parts[0] === "daily" && parts.length === 3) {
    return `${SCHEDULE_LABELS.daily[lang]} ${parts[1]}:${parts[2]}`;
  }
  if (parts[0] === "weekdays" && parts.length === 3) {
    return `${SCHEDULE_LABELS.weekdays[lang]} ${parts[1]}:${parts[2]}`;
  }
  if (parts[0] === "weekly" && parts.length === 4) {
    const day = lookup(DOW_LABELS, parts[1].toUpperCase(), lang);
    return `${SCHEDULE_LABELS.weekly[lang]}${lang === "zh" ? "" : " "}${day} ${parts[2]}:${parts[3]}`;
  }
  return schedule;
}

/** Backend UI language ("zh-CN"/"en-US") → presentation key. */
export function uiLang(language: string): UiLanguage {
  return language.startsWith("zh") ? "zh" : "en";
}
