import type { ReactNode } from "react";

/**
 * Guanlan port — Badge（G0 基础组件集，方案 §31）。
 * mono 小字状态芯片；语义色全部走 token（up=涨红/down=跌绿/error=danger 独立）。
 */

export type BadgeTone = "neutral" | "ok" | "error" | "warning" | "up" | "down";

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
}

export function Badge({ tone = "neutral", children }: BadgeProps) {
  const cls = tone === "neutral" ? "gl-badge" : `gl-badge gl-badge-${tone}`;
  return <span className={cls}>{children}</span>;
}
