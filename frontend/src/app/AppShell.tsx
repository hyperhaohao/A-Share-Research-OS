import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { NAV_GROUPS } from "./navigation";
import { AppearanceControls, LanguageControls } from "../components/AppearanceControls";

/**
 * AppShell（任务书 §5/§6/§42）：左侧分组 Sidebar + TopContextBar + 内容区。
 * 220px 展开 / 64px 收起；分组可折叠；当前模块高亮；外观/语言在 Sidebar 底部。
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(NAV_GROUPS.map((g) => [g.key, true])),
  );

  const toggleGroup = (key: string) =>
    setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className={`app-shell ${collapsed ? "shell-collapsed" : ""}`}>
      <aside className="sidebar" data-testid="sidebar">
        <div className="sidebar-brand">
          <NavLink to="/" className="brand-link" end>
            {collapsed ? "AS" : t("app.name")}
          </NavLink>
          <button
            type="button"
            className="sidebar-collapse"
            aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>

        <nav className="sidebar-nav" aria-label={t("nav.dashboard")}>
          <NavLink
            to="/"
            end
            className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            title={t("nav.dashboard")}
          >
            {!collapsed && <span className="sidebar-label">{t("nav.dashboard")}</span>}
          </NavLink>

          {NAV_GROUPS.map((group) => (
            <div className="sidebar-group" key={group.key}>
              <button
                type="button"
                className="sidebar-group-toggle"
                aria-expanded={openGroups[group.key]}
                onClick={() => toggleGroup(group.key)}
                title={t(group.labelKey)}
              >
                <span className="sidebar-label">{t(group.labelKey)}</span>
                {!collapsed && <span className="group-caret">{openGroups[group.key] ? "▾" : "▸"}</span>}
              </button>
              {openGroups[group.key] &&
                group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => `sidebar-link sub${isActive ? " active" : ""}`}
                    title={t(item.labelKey)}
                  >
                    {!collapsed && <span className="sidebar-label">{t(item.labelKey)}</span>}
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <AppearanceControls stacked />
          <LanguageControls stacked />
        </div>
      </aside>

      <div className="shell-main">{children}</div>
    </div>
  );
}
