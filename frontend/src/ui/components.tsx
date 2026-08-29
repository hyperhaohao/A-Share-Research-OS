import { useTranslation } from "react-i18next";

/**
 * Semantic components（任务书 §8/§44）：最小语义集，直接服务真实页面。
 * 不做空 Storybook 工程。
 */

export function StatusBadge({
  status,
  tone = "neutral",
}: {
  status: string;
  tone?: "ok" | "error" | "warning" | "neutral";
}) {
  return (
    <span className={`status-badge tone-${tone}`} data-status={status}>
      {status}
    </span>
  );
}

export function SectionHeader({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="section-header">
      <h2>{title}</h2>
      {hint && <span className="secondary">{hint}</span>}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <p>{title}</p>
      {hint && <p className="secondary">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, retry }: { message?: string; retry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="error-state" role="alert" data-testid="error-state">
      <p className="status-error">{message ?? t("common.error")}</p>
      {retry && (
        <button type="button" className="control-btn" onClick={retry}>
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

export function TechnicalDetails({
  summary = "技术详情",
  children,
}: {
  summary?: string;
  children: React.ReactNode;
}) {
  return (
    <details className="technical-details">
      <summary className="secondary">{summary}</summary>
      {children}
    </details>
  );
}
