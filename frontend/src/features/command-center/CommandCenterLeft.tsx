import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Panel, ResearchStep } from "../../ui/guanlan";
import { formatTaskStatus, uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import { useInstrumentName } from "../../shared/instrument";
import { stepIndex, stepToInkStatus, type Plan } from "./plan";

interface RunItem {
  run_id: string;
  instrument_id: string;
  status: string;
  started_at: string | null;
}

interface TaskItem {
  task_id: string;
  instrument_id: string;
  status: string;
}

/**
 * 左栏（donor LeftRail 行为 → ASRO 数据，方案 §6 计划区）：
 * 当前计划墨痕（ResearchStep 三态）+ 正在运行 + 最近计划 + 研究对话会话。
 */
export function CommandCenterLeft({
  activePlan,
  plans,
  runningRuns,
  activeTasks,
  sessionId,
  onSessionChange,
}: {
  activePlan: Plan | null;
  plans: Plan[];
  runningRuns: RunItem[];
  activeTasks: TaskItem[];
  sessionId: string | null;
  onSessionChange: (id: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <Panel title={t("commander.currentPlan")}>
        <div data-testid="commander-current-plan">
          {activePlan ? (
            <PlanInkSteps plan={activePlan} />
          ) : (
            <p className="secondary">{t("commander.noPlanYet")}</p>
          )}
        </div>
      </Panel>

      <Panel title={t("commander.runningNow")}>
        {runningRuns.length === 0 && activeTasks.length === 0 ? (
          <p className="secondary">{t("commandCenter.noResearchYet")}</p>
        ) : (
          <ul className="watch-list">
            {runningRuns.map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
            {activeTasks.map((task) => (
              <TaskRow key={task.task_id} task={task} />
            ))}
          </ul>
        )}
        <p>
          <Link to="/tasks" className="secondary">
            {t("commandCenter.goTasks")} →
          </Link>
        </p>
      </Panel>

      <Panel title={t("commander.recentPlans")}>
        {plans.length === 0 && (
          <p className="secondary">{t("commandCenter.noResearchYet")}</p>
        )}
        <ul className="watch-list">
          {plans.map((plan) => (
            <PlanRow key={plan.plan_id} plan={plan} />
          ))}
        </ul>
      </Panel>

      <Panel title={t("cc.pendingConfirmations")}>
        <div data-testid="pending-confirmations">
          <PendingConfirmationsPanel />
        </div>
      </Panel>

      <Panel title={t("cc.backgroundTasks")}>
        <div data-testid="background-tasks">
          <BackgroundTasksPanel />
        </div>
      </Panel>

      <SessionSwitcher sessionId={sessionId} onSessionChange={onSessionChange} />
    </>
  );
}

/** 未处理确认（F7 服务端真实状态；批准/拒绝走 §8.6 状态机）。 */
function PendingConfirmationsPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const pendingQuery = useQuery({
    queryKey: ["cc-confirmations-pending"],
    refetchInterval: 5000,
    queryFn: async (): Promise<Array<{ confirmation_id: string; tool_name: string }>> => {
      const resp = await fetch("/api/v1/command/confirmations?status=pending");
      if (!resp.ok) return [];
      const body = (await resp.json()) as {
        results: Array<{ confirmation_id: string; tool_name: string }>;
      };
      return body.results ?? [];
    },
  });

  const decideMutation = useMutation({
    mutationFn: async (input: { id: string; decision: "approved" | "rejected" }) => {
      const resp = await fetch(
        `/api/v1/command/confirmations/${input.id}/decide`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision: input.decision }) },
      );
      if (!resp.ok) throw new Error("confirmation.decide_failed");
      return resp.json();
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["cc-confirmations-pending"] }),
  });

  const pending = pendingQuery.data ?? [];
  if (pending.length === 0) {
    return <p className="secondary">{t("cc.noPendingConfirmations")}</p>;
  }
  return (
    <ul className="watch-list">
      {pending.map((c) => (
        <li key={c.confirmation_id} className="result-row">
          <span className="mono cc-confirm-tool">{c.tool_name}</span>
          <span className="cc-card-actions">
            <button
              type="button"
              className="gl-button gl-button-primary"
              data-testid={"confirm-approve-" + c.confirmation_id}
              aria-label={t("cc.confirmApprove")}
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate({ id: c.confirmation_id, decision: "approved" })}
            >
              {t("cc.confirmApprove")}
            </button>
            <button
              type="button"
              className="gl-button gl-button-ghost"
              data-testid={"confirm-reject-" + c.confirmation_id}
              aria-label={t("cc.confirmReject")}
              disabled={decideMutation.isPending}
              onClick={() => decideMutation.mutate({ id: c.confirmation_id, decision: "rejected" })}
            >
              {t("cc.confirmReject")}
            </button>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** 后台任务（F9 跑道：状态 + 进度 + 恢复入口）。 */
function BackgroundTasksPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({
    queryKey: ["cc-background-tasks"],
    refetchInterval: 5000,
    queryFn: async (): Promise<
      Array<{ task_id: string; tool_name: string; status: string; progress: number }>
    > => {
      const resp = await fetch("/api/v1/command/tasks?limit=6");
      if (!resp.ok) return [];
      const body = (await resp.json()) as {
        results: Array<{ task_id: string; tool_name: string; status: string; progress: number }>;
      };
      return body.results ?? [];
    },
  });

  const retryMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const resp = await fetch(`/api/v1/command/tasks/${taskId}/retry`, { method: "POST" });
      if (!resp.ok) throw new Error("task.retry_failed");
      return resp.json();
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["cc-background-tasks"] }),
  });

  const tasks = tasksQuery.data ?? [];
  if (tasks.length === 0) {
    return <p className="secondary">{t("cc.noBackgroundTasks")}</p>;
  }
  return (
    <ul className="watch-list">
      {tasks.map((task) => (
        <li key={task.task_id} className="result-row" data-testid={"bg-task-" + task.status}>
          <span className="mono">{task.tool_name}</span>
          <span
            className={
              task.status === "failed"
                ? "status-error"
                : task.status === "succeeded"
                  ? "status-ok"
                  : "secondary"
            }
          >
            {t(`cc.taskStatus.${task.status}`, { defaultValue: task.status })}
            {task.progress > 0 ? ` · ${task.progress}%` : ""}
          </span>
          {(task.status === "failed" || task.status === "cancelled") && (
            <button
              type="button"
              className="gl-button gl-button-ghost"
              data-testid={"task-retry-" + task.task_id}
              onClick={() => retryMutation.mutate(task.task_id)}
            >
              {t("cc.taskRetry")}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

/** 当前计划 → donor 墨痕步骤行（§6 左：计划实时更新）。 */
function PlanInkSteps({ plan }: { plan: Plan }) {
  return (
    <div className="plan-steps">
      {plan.steps.map((step, i) => (
        <div key={step.step_id}>
          <ResearchStep
            step={stepIndex(i)}
            label={step.title}
            status={stepToInkStatus(step.status)}
          />
          {step.detail && step.status === "running" && (
            <p className="secondary cc-step-detail">{step.detail}</p>
          )}
          {step.error && <p className="status-error cc-step-detail">{step.error}</p>}
        </div>
      ))}
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

function RunRow({ run }: { run: RunItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(run.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/instrument/${run.instrument_id}`} className="result-name">
        {profile?.name ?? run.instrument_id}
      </Link>
      <span className="secondary">{formatWhen(run.started_at, lang)}</span>
      <span
        className={
          run.status === "failed"
            ? "status-error"
            : run.status === "succeeded"
              ? "status-ok"
              : "secondary"
        }
      >
        {t(`commandCenter.runStatus.${run.status}`, { defaultValue: run.status })}
      </span>
    </li>
  );
}

function TaskRow({ task }: { task: TaskItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(task.instrument_id);
  return (
    <li className="result-row">
      <Link to={`/instrument/${task.instrument_id}`}>
        {profile?.name ?? task.instrument_id}
      </Link>
      <span>{formatTaskStatus(task.status, lang)}</span>
      <Link to="/tasks" className="secondary">
        {t("commandCenter.viewTask")}
      </Link>
    </li>
  );
}

export function PlanRow({ plan }: { plan: Plan }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const profile = useInstrumentName(plan.instrument_id);
  return (
    <li className="result-row" data-testid="plan-row">
      <span className="result-name">
        {plan.title}
        {profile ? ` · ${profile.name}` : ""}
      </span>
      <span
        className={
          plan.status === "failed"
            ? "status-error"
            : plan.status === "completed"
              ? "status-ok"
              : "secondary"
        }
      >
        {t(`commander.status.${plan.status}`)}
      </span>
      <span className="secondary">{formatWhen(plan.updated_at, lang)}</span>
    </li>
  );
}

/** 研究对话会话切换（donor 多会话行为；后端 command_sessions 持久化）。 */
function SessionSwitcher({
  sessionId,
  onSessionChange,
}: {
  sessionId: string | null;
  onSessionChange: (id: string) => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);

  const sessionsQuery = useQuery({
    queryKey: ["command-sessions-list"],
    enabled: sessionId != null,
    queryFn: async (): Promise<Array<{ session_id: string; created_at: string | null }>> => {
      const resp = await fetch("/api/v1/command/sessions?limit=8");
      if (!resp.ok) return [];
      const body = (await resp.json()) as {
        results: Array<{ session_id: string; created_at: string | null }>;
      };
      return body.results;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (): Promise<string> => {
      const resp = await fetch("/api/v1/command/sessions", { method: "POST" });
      if (!resp.ok) throw new Error("network.unreachable");
      const body = (await resp.json()) as { session: { session_id: string } };
      return body.session.session_id;
    },
    onSuccess: (id) => {
      setCreating(false);
      onSessionChange(id);
      void queryClient.invalidateQueries({ queryKey: ["command-sessions-list"] });
    },
    onError: () => setCreating(false),
  });

  const sessions = sessionsQuery.data ?? [];
  return (
    <Panel
      title={t("cc.sessions")}
      actions={
        <button
          type="button"
          className="gl-button gl-button-ghost"
          data-testid="commander-new-session"
          disabled={creating || createMutation.isPending}
          onClick={() => {
            setCreating(true);
            createMutation.mutate();
          }}
        >
          + {t("cc.newSession")}
        </button>
      }
    >
      {sessions.length === 0 ? (
        <p className="secondary">{t("cc.noSessions")}</p>
      ) : (
        <ul className="watch-list cc-session-list">
          {sessions.map((s) => (
            <li key={s.session_id} className="result-row">
              <button
                type="button"
                className={`cc-session-link${s.session_id === sessionId ? " cc-session-active" : ""}`}
                onClick={() => onSessionChange(s.session_id)}
              >
                {s.session_id === sessionId
                  ? t("cc.currentSession")
                  : t("cc.pastSession")}
              </button>
              <SessionTime iso={s.created_at} />
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function SessionTime({ iso }: { iso: string | null }) {
  const { i18n } = useTranslation();
  return <span className="secondary">{formatWhen(iso, uiLang(i18n.language))}</span>;
}
