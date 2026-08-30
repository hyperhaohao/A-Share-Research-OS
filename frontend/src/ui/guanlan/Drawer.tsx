import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

/**
 * Guanlan port — Drawer（G0 基础组件集，方案 §31）。
 * 右侧滑出抽屉：scrim 点击 / Esc / 关闭钮三种退出；focus 落在关闭钮。
 */

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  width?: number;
  children: ReactNode;
}

export function Drawer({ open, onClose, title, width = 420, children }: DrawerProps) {
  const { t } = useTranslation();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    closeRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <>
      <div className="gl-drawer-scrim" onClick={onClose} aria-hidden="true" />
      <aside className="gl-drawer" style={{ width }} role="dialog" aria-modal="true" aria-label={title ?? t("guanlan.drawerTitle")}>
        <header className="gl-drawer-header">
          {title && <h3 className="gl-drawer-title">{title}</h3>}
          <button ref={closeRef} type="button" className="gl-drawer-close" onClick={onClose} aria-label={t("guanlan.drawerClose")}>
            ✕
          </button>
        </header>
        <div className="gl-drawer-body">{children}</div>
      </aside>
    </>
  );
}
