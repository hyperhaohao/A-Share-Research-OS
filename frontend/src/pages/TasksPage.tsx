import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface TaskItem {
  task_id: string;
  instrument_id: string;
  task_type: string;
  schedule: string;
  enabled: boolean;
  status: string;
  attempts: number;
  last_run_at: string | null;
  next_run_at: string | null;
}

interface TickResult {
  claimed: string[];
  succeeded: string[];
  failed: string[];
  recovered: string[];
}

async function fetchTasks(): Promise<TaskItem[]> {
  const resp = await fetch("/api/v1/tasks");
  if (!resp.ok) throw new Error("network.unreachable");
  const body = await resp.json();
  return body.results;
}

async function createTask(payload: { instrument: string; task_type: string; schedule: string }) {
  const resp = await fetch("/api/v1/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error("instrument.not_found");
  return resp.json();
}

async function setEnabled(taskId: string, enabled: boolean) {
  const resp = await fetch(`/api/v1/tasks/${taskId}?enabled=${enabled}`, { method: "PATCH" });
  if (!resp.ok) throw new Error("task.not_found");
}

async function tickScheduler(): Promise<TickResult> {
  const resp = await fetch("/api/v1/tasks/scheduler/tick", { method: "POST" });
  return resp.json();
}

export function TasksPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [instrument, setInstrument] = useState("");
  const [taskType, setTaskType] = useState("monitor");

  const tasksQuery = useQuery({ queryKey: ["tasks"], queryFn: fetchTasks, refetchInterval: 5000 });
  const tickMutation = useMutation({
    mutationFn: tickScheduler,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const createMutation = useMutation({
    mutationFn: () =>
      createTask({ instrument: instrument.trim(), task_type: taskType, schedule: "interval:0" }),
    onSuccess: () => {
      setInstrument("");
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
  const toggleMutation = useMutation({
    mutationFn: ({ taskId, enabled }: { taskId: string; enabled: boolean }) =>
      setEnabled(taskId, enabled),
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
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            aria-label={t("tasks.type")}
          >
            <option value="monitor">{t("tasks.typeMonitor")}</option>
            <option value="prediction_validation">{t("tasks.typeValidation")}</option>
          </select>
          <button type="submit" className="control-btn">
            {t("tasks.add")}
          </button>
        </form>
        {createMutation.isError && <p className="status-error">{t("common.error")}</p>}
      </section>

      <section className="card">
        <h2>{t("tasks.scheduler")}</h2>
        <button type="button" className="control-btn" onClick={() => tickMutation.mutate()} disabled={tickMutation.isPending}>
          {t("tasks.tick")}
        </button>
        {tickMutation.data && (
          <p className="mono secondary" data-testid="tick-result">
            {t("tasks.tickRan", { claimed: tickMutation.data.claimed.length, ok: tickMutation.data.succeeded.length })}
          </p>
        )}
      </section>

      <section className="card">
        <h2>{t("tasks.list")}</h2>
        <ul className="watch-list">
          {(tasksQuery.data ?? []).map((task) => (
            <li key={task.task_id} className="result-row">
              <span className="mono">{task.instrument_id}</span>
              <span className="mono secondary">{task.task_type}</span>
              <span className={task.status === "failed" ? "status-error mono" : "mono secondary"}>
                {task.status}
              </span>
              <button
                type="button"
                className="control-btn"
                onClick={() =>
                  toggleMutation.mutate({ taskId: task.task_id, enabled: !task.enabled })
                }
              >
                {task.enabled ? t("tasks.disable") : t("tasks.enable")}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
