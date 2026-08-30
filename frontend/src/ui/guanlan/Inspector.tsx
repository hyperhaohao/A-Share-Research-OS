import type { ReactNode } from "react";

/**
 * Guanlan port — Inspector（G0 基础组件集，方案 §31）。
 * 三栏工作台的右栏详情面板（G5 选股 / G4 工作流 / G2 产业环节详情共用壳）。
 */

export interface InspectorProps {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function Inspector({ title, actions, children }: InspectorProps) {
  return (
    <aside className="guanlan-inspector">
      <header className="guanlan-inspector-header">
        <h3 className="guanlan-inspector-title">{title}</h3>
        {actions && <div className="gl-panel-actions">{actions}</div>}
      </header>
      <div className="guanlan-inspector-body">{children}</div>
    </aside>
  );
}
