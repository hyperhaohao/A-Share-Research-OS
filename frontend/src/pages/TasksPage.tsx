import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  formatBoard,
  formatExchange,
  formatSchedule,
  formatTaskStatus,
  formatTaskType,
  uiLang,
} from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

interface TaskItem {
  task_id: string;
  instrument_id: string;
  task_type: string;
  schedule: string;
  research_level: string;
  enabled: boolean;
  status: string;
  attempts: number;
  last_run_at: string | null;
  next_run_at: string | null;
}

interface Profile {
  code: string;
  name: string;
  exchange: string;
  board: string;
}

async function fetchTasks(): Promise<TaskItem[]> {
  const resp = await fetch("/api/v1/tasks");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
}

async function createTask(payload: {
  instrument: string;
  task_type: string;
  schedule: string;
}): Promise<void> {
  const resp = await fetch("/api/v1/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
}

async function setEnabled(taskId: string, enabled: boolean): Promise<void> {
  const resp = await fetch(`/api/v1/tasks/${taskId}?enabled=${enabled}`, { method: "PATCH" });
  if (!resp.ok) throw new Error("task.not_found");
}

async function deleteTask(taskId: string): Promise<void> {
  const resp = await fetch(`/api/v1/tasks/${taskId}`, { method: "DELETE" });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
}

async function runNow(taskId: string): Promise<void> {
  const resp = await fetch(`/api/v1/tasks/${taskId}/run`, { method: "POST" });
  if (!resp.ok) {
    const body = (await resp.json().catch(() => null)) as { error_code?: string } | null;
    throw new Error(body?.error_code ?? "network.unreachable");
  }
}

/** Identity lookup reused by every task card (registry-backed, cheap). */
function useProfile(instrumentId: string | null): Profile | null {
  const { data } = useQuery({
    queryKey: ["instrument", instrumentId],
    enabled: instrumentId != null,
    staleTime: 60000,
    queryFn: async () => {
      const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(instrumentId ?? "")}`);
      if (!resp.ok) return null;
      const body = await resp.json();
      return body.instrument as Profile;
    },
  });
  return data ?? null;
}

function TaskCard({ task }: { task: TaskItem }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const profile = useProfile(task.instrument_id);

  const reportQuery = useQuery({
    queryKey: ["reports", task.instrument_id],
    queryFn: async (): Promise<{ report_id: string; created_at: string | null } | null> => {
      const resp = await fetch(
        `/api/v1/reports?instrument_id=${encodeURIComponent(task.instrument_id)}`,
      );
      if (!resp.ok) return null;
      const body = await resp.json();
      return (body.results?.[0] as { report_id: string; created_at: string | null }) ?? null;
    },
  });
  const latestReport = reportQuery.data;

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: ["tasks"] });

  const runMutation = useMutation({
    mutationFn: () => runNow(task.task_id),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (err: Error) => setActionError(err.message),
  });
  const toggleMutation = useMutation({
    mutationFn: () => setEnabled(task.task_id, !task.enabled),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (err: Error) => setActionError(err.message),
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteTask(task.task_id),
    onSuccess: () => invalidate(),
    onError: (err: Error) => {
      setActionError(err.message);
      setConfirming(false);
    },
  });

  return (
    <li className="card watch-card" data-testid="task-card">
      <div className="watch-card-head">
        <Link to={`/instrument/${task.instrument_id}`} className="watch-card-name">
          {profile?.name ?? task.instrument_id}
        </Link>
        {profile && (
          <span className="secondary">
            {profile.code} · {formatExchange(profile.exchange, lang)}
            {profile.board ? ` · ${formatBoard(profile.board, lang)}` : ""}
          </span>
        )}
      </div>

      <div className="task-grid">
        <span>{t("tasks.typeLabel")}</span>
        <span>{formatTaskType(task.task_type, lang)}</span>
        <span>{t("tasks.scheduleLabel")}</span>
        <span className="mono">{formatSchedule(task.schedule, lang)}</span>
        <span>{t("tasks.statusLabel")}</span>
        <span className={task.status === "failed" ? "status-error" : ""}>
          {formatTaskStatus(task.status, lang)}
        </span>
        <span>{t("tasks.lastRun")}</span>
        <span>{task.last_run_at ? formatWhen(task.last_run_at, lang) : "—"}</span>
        <span>{t("tasks.nextRun")}</span>
        <span>{task.next_run_at ? formatWhen(task.next_run_at, lang) : "—"}</span>
      </div>

      {actionError && (
        <p className="status-error">
          {actionError === "task.running"
            ? t("tasks.runningRefusal")
            : t(`errors.${actionError}`, { defaultValue: t("common.error") })}
        </p>
      )}

      <div className="header-controls">
        {latestReport && (
          <Link className="control-btn" to={`/reports/${latestReport.report_id}`}>
            {t("tasks.openLatestReport")}
          </Link>
        )}
        <button type="button" className="control-btn" onClick={() => runMutation.mutate()}>
          {t("tasks.runNow")}
        </button>
        <button type="button" className="control-btn" onClick={() => toggleMutation.mutate()}>
          {task.enabled ? t("tasks.disable") : t("tasks.enable")}
        </button>
        {confirming ? (
          <>
            <span className="secondary">{t("tasks.deleteConfirmText")}</span>
            <button
              type="button"
              className="control-btn"
              onClick={() => deleteMutation.mutate()}
            >
              {t("tasks.deleteConfirmYes")}
            </button>
            <button
              type="button"
              className="control-btn"
              onClick={() => setConfirming(false)}
            >
              {t("tasks.deleteConfirmNo")}
            </button>
          </>
        ) : (
          <button type="button" className="control-btn" onClick={() => setConfirming(true)}>
            {t("tasks.delete")}
          </button>
        )}
      </div>
    </li>
  );
}

type Frequency = "daily" | "weekdays" | "weekly";

export function TasksPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [instrument, setInstrument] = useState(searchParams.get("instrument") ?? "");
  const [taskType, setTaskType] = useState("monitor");
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [weeklyDay, setWeeklyDay] = useState("MON");
  const [timeOfDay, setTimeOfDay] = useState("08:30");
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  useEffect(() => {
    const prefill = searchParams.get("instrument");
    if (prefill) setInstrument(prefill);
  }, [searchParams]);

  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
    refetchInterval: 5000,
  });

  const schedule = (() => {
    const [hh, mm] = timeOfDay.split(":");
    if (frequency === "weekly") return `weekly:${weeklyDay}:${hh}:${mm}`;
    return `${frequency}:${hh}:${mm}`;
  })();

  const createMutation = useMutation({
    mutationFn: () =>
      createTask({ instrument: instrument.trim(), task_type: taskType, schedule }),
    onSuccess: () => {
      setInstrument("");
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const tickMutation = useMutation({
    mutationFn: async (): Promise<{ claimed: string[]; succeeded: string[] }> => {
      const resp = await fetch("/api/v1/tasks/scheduler/tick", { method: "POST" });
      return resp.json();
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (instrument.trim()) createMutation.mutate();
  };

  return (
    <main className="page" data-testid="tasks-page">
      <h1>{t("nav.tasks")}</h1>

      <section className="card">
        <h2>{t("tasks.create")}</h2>
        <form onSubmit={onSubmit} className="search-form">
          <input
            type="text"
            value={instrument}
            onChange={(e) => setInstrument(e.target.value)}
            placeholder={t("home.searchPlaceholder")}
            aria-label={t("tasks.create")}
          />
          <select
            className="control-select"
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            aria-label={t("tasks.type")}
          >
            <option value="monitor">{t("tasks.typeMonitor")}</option>
            <option value="prediction_validation">{t("tasks.typeValidation")}</option>
            <option value="periodic_full_research">{t("tasks.typeFull")}</option>
          </select>
          <select
            className="control-select"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as Frequency)}
            aria-label={t("tasks.frequency")}
          >
            <option value="daily">{t("tasks.freqDaily")}</option>
            <option value="weekdays">{t("tasks.freqWeekdays")}</option>
            <option value="weekly">{t("tasks.freqWeekly")}</option>
          </select>
          {frequency === "weekly" && (
            <select
              className="control-select"
              value={weeklyDay}
              onChange={(e) => setWeeklyDay(e.target.value)}
              aria-label={t("tasks.weekday")}
            >
              {["MON", "TUE", "WED", "THU", "FRI"].map((d) => (
                <option key={d} value={d}>
                  {t(`tasks.day.${d}`)}
                </option>
              ))}
            </select>
          )}
          <input
            type="time"
            value={timeOfDay}
            onChange={(e) => setTimeOfDay(e.target.value)}
            aria-label={t("tasks.time")}
          />
          <button type="submit" className="control-btn">
            {t("tasks.add")}
          </button>
        </form>
        {createMutation.isError && (
          <p className="status-error">
            {createMutation.error.message === "task.schedule_invalid"
              ? t("tasks.scheduleInvalid")
              : t(`errors.${createMutation.error.message}`, { defaultValue: t("common.error") })}
          </p>
        )}
      </section>

      <section className="card">
        <h2>{t("tasks.list")}</h2>
        {tasksQuery.isPending && <p className="secondary">{t("common.loading")}</p>}
        {tasksQuery.data?.length === 0 && (
          <p className="secondary">{t("tasks.empty")}</p>
        )}
        <ul className="watch-list watch-cards">
          {(tasksQuery.data ?? []).map((task) => (
            <TaskCard key={task.task_id} task={task} />
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>{t("tasks.diagnostics")}</h2>
        <p className="secondary">{t("tasks.diagnosticsHint")}</p>
        <button
          type="button"
          className="control-btn"
          onClick={() => setShowDiagnostics((v) => !v)}
        >
          {t("tasks.techDetails")}
        </button>
        {showDiagnostics && (
          <div className="mono secondary">
            <button
              type="button"
              className="control-btn"
              onClick={() => tickMutation.mutate()}
              disabled={tickMutation.isPending}
            >
              {t("tasks.tick")}
            </button>
            {tickMutation.data && (
              <p data-testid="tick-result">
                {t("tasks.tickRan", {
                  claimed: tickMutation.data.claimed.length,
                  ok: tickMutation.data.succeeded.length,
                })}
              </p>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
