import type { ReactNode } from "react";

/**
 * Guanlan port — Panel（G0 基础组件集，方案 §31）。
 * 纸面卡片：可选标题行（serif 标题 + mono 提示 + 右侧动作区）+ 内容区。
 * 迁植页面的容器统一用它，替换 donor 散落的 inline-style panel。
 */

export interface PanelProps {
  title?: string;
  hint?: string;
  actions?: ReactNode;
  flush?: boolean;
  className?: string;
  children?: ReactNode;
}

export function Panel({ title, hint, actions, flush, className, children }: PanelProps) {
  const header = title || actions;
  return (
    <section className={`gl-panel${className ? ` ${className}` : ""}`}>
      {header && (
        <header className={`gl-panel-header${flush ? " gl-panel-header-flush" : ""}`}>
          {title && <h3 className="gl-panel-title">{title}</h3>}
          {hint && <span className="gl-panel-hint">{hint}</span>}
          {actions && <div className="gl-panel-actions">{actions}</div>}
        </header>
      )}
      <div className="gl-panel-body">{children}</div>
    </section>
  );
}
