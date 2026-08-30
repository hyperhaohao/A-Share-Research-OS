import type { ReactNode } from "react";

/**
 * Guanlan port — Toolbar（G0 基础组件集，方案 §31）。
 * 水平控件条；分隔线用 <Toolbar.Sep />。
 */

export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`gl-toolbar${className ? ` ${className}` : ""}`}>{children}</div>;
}

export function ToolbarSep() {
  return <span className="gl-toolbar-sep" aria-hidden="true" />;
}
