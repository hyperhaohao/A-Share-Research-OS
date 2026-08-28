/**
 * Presentation layer (PW0): human-readable formatting helpers.
 *
 * Times render as "今天 18:32" style; numbers/percentages get one format.
 * Tech IDs (run_id / report_id / task_id ...) never pass through here —
 * they only appear inside each page's collapsed "技术详情" section.
 */

import type { UiLanguage } from "./enumLabels";

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/** "今天 18:32" / "昨天 09:00" / "2026-08-28" (cross-year) */
export function formatWhen(
  iso: string | null | undefined,
  lang: UiLanguage,
  now: Date = new Date(),
): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  if (isSameDay(d, now)) {
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return lang === "zh" ? `今天 ${hm}` : `Today ${hm}`;
  }
  if (isSameDay(d, yesterday)) {
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return lang === "zh" ? `昨天 ${hm}` : `Yesterday ${hm}`;
  }
  const crossYear = d.getFullYear() !== now.getFullYear();
  if (crossYear) {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** +2.31% / -1.20% / — (null-safe) */
export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** thousands separators, fixed digits, null-safe */
export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
