import type { ReactNode } from "react";

/**
 * Guanlan port — Tooltip（G0 基础组件集，方案 §31）。
 * CSS 悬停提示：hover / focus-within 时 ::after 显示 data-tip。
 * 提示文案必须本地化后再传入（方案 §27）。
 */

export interface TooltipProps {
  tip: string;
  children: ReactNode;
}

export function Tooltip({ tip, children }: TooltipProps) {
  return (
    <span className="gl-tooltip" data-tip={tip} tabIndex={0}>
      {children}
    </span>
  );
}
