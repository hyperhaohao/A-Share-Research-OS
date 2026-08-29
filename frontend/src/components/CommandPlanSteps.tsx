import { useTranslation } from "react-i18next";
import { useInstrumentName } from "../shared/instrument";

export interface PlanStep {
  step_id: string;
  title: string;
  action: string;
  status: string;
  artifact_ids: string[];
  detail: string | null;
  error: string | null;
}

export interface Plan {
  plan_id: string;
  session_id: string | null;
  instrument_id: string | null;
  title: string;
  status: string;
  steps: PlanStep[];
  run_id: string | null;
  error: string | null;
  updated_at?: string | null;
}

const STEP_STATUS_KEY: Record<string, string> = {
  pending: "commander.stepPending",
  running: "commander.stepRunning",
  ok: "commander.stepOk",
  failed: "commander.stepFailed",
};

/** 左栏/中栏共用的计划步骤渲染（总纲 §38 左栏直接渲染 ResearchPlan）。 */
export function CommandPlanSteps({
  plan,
  compact = false,
  "data-testid": testid,
}: {
  plan: Plan;
  compact?: boolean;
  "data-testid"?: string;
}) {
  const { t } = useTranslation();
  return (
    <div className="plan-steps" data-testid={testid}>
      {!compact && <h3 className="plan-title">{plan.title}</h3>}
      <ul className="result-list">
        {plan.steps.map((step) => (
          <li
            key={step.step_id}
            className={`plan-step stage-${step.status === "ok" ? "done" : step.status}`}
          >
            <span className="plan-step-status">{t(STEP_STATUS_KEY[step.status] ?? step.status)}</span>
            <span className="plan-step-title">{step.title}</span>
            {!compact && step.detail && <span className="secondary">{step.detail}</span>}
            {step.error && <span className="status-error">{step.error}</span>}
          </li>
        ))}
      </ul>
      <PlanStatusLine plan={plan} />
    </div>
  );
}

function PlanStatusLine({ plan }: { plan: Plan }) {
  const { t } = useTranslation();
  const profile = useInstrumentName(plan.instrument_id);
  if (plan.status === "running") {
    return <p className="secondary">{t("commander.planRunning")}</p>;
  }
  if (plan.status === "failed") {
    return <p className="status-error">{t("commander.planFailed")}: {plan.error}</p>;
  }
  return (
    <p className="status-ok">
      {t("commander.planCompleted")}
      {profile ? ` · ${profile.name}` : ""}
    </p>
  );
}

/** 状态徽标（左栏列表用）。 */
export function PlanStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span className={status === "failed" ? "status-error" : status === "completed" ? "status-ok" : "secondary"}>
      {t(`commander.status.${status}`)}
    </span>
  );
}

export function PlanTitle({ plan }: { plan: Plan }) {
  const profile = useInstrumentName(plan.instrument_id);
  return (
    <span>
      {plan.title}
      {profile ? ` · ${profile.name}` : ""}
    </span>
  );
}
