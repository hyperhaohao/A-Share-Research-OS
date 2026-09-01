/**
 * 帷幄事件线程（F10，任务书 §8.10 中栏）：
 * User/Assistant 消息 + Plan/Tool Call/Tool Result/Confirmation/
 * Background Task/Artifact/Error 卡片 —— 全部由 F5 事件协议驱动
 * （append-only 回放 + EventSource live；polling 为无 EventSource
 * 环境的回退）。卡片动作（批准/拒绝）直接走 F7 审批门。
 */

import { useEffect, useMemo, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

export interface CommandEvent {
  event_id: string;
  session_id: string;
  sequence: number;
  event_type: string;
  created_at: string | null;
  correlation_id: string | null;
  plan_id: string | null;
  task_id: string | null;
  status: string | null;
  payload: Record<string, unknown>;
  artifact_ids: string[];
  provenance: Record<string, unknown>;
}

async function fetchEvents(sessionId: string, after: number): Promise<CommandEvent[]> {
  const resp = await fetch(
    `/api/v1/command/sessions/${sessionId}/events?after_sequence=${after}&limit=200`,
  );
  if (!resp.ok) return [];
  const body = (await resp.json()) as { results: CommandEvent[] };
  return body.results ?? [];
}

/** 事件线程：SSE live（EventSource 可用时）+ polling 兜底；sequence 去重。 */
export function EventThread({ sessionId }: { sessionId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const eventsQuery = useQuery({
    queryKey: ["cc-events", sessionId],
    enabled: sessionId != null,
    refetchInterval: 4000,
    queryFn: () => fetchEvents(sessionId, 0),
  });

  const events = useMemo(() => {
    const seen = new Set<string>();
    const unique = (eventsQuery.data ?? []).filter((e) => {
      if (seen.has(e.event_id)) return false;
      seen.add(e.event_id);
      return true;
    });
    return unique.sort((a, b) => a.sequence - b.sequence);
  }, [eventsQuery.data]);

  const lastSequence = events.length > 0 ? events[events.length - 1].sequence : 0;

  // Live SSE（任务书 §8.4：真实 SSE 消费；stream_end/reconnect 由
  // EventSource retry 头处理；sequence 去重保证不重复展示）
  useEffect(() => {
    if (sessionId == null || typeof EventSource === "undefined") return;
    let closed = false;
    const source = new EventSource(
      `/api/v1/command/sessions/${sessionId}/stream?after_sequence=${lastSequence}`,
    );
    source.onmessage = () => {
      if (!closed) {
        void queryClient.invalidateQueries({ queryKey: ["cc-events", sessionId] });
      }
    };
    const refresh = (): void => {
      if (!closed) {
        void queryClient.invalidateQueries({ queryKey: ["cc-events", sessionId] });
      }
    };
    source.addEventListener("tool_call", refresh);
    source.addEventListener("tool_result", refresh);
    source.addEventListener("tool_error", refresh);
    source.addEventListener("confirmation_requested", refresh);
    source.addEventListener("confirmation_decided", refresh);
    source.addEventListener("task_completed", refresh);
    source.addEventListener("task_failed", refresh);
    source.addEventListener("run_completed", refresh);
    source.addEventListener("run_failed", refresh);
    return () => {
      closed = true;
      source.close();
    };
    // lastSequence 只在挂载/会话变化时取一次，避免每事件重连
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [events.length]);

  const cardEvents = events.filter((e) => !isTurnDuplicate(e));

  return (
    <div className="cc-event-thread" data-testid="cc-event-thread">
      {cardEvents.map((event) => (
        <EventCard key={event.event_id} event={event} sessionId={sessionId} />
      ))}
      <div ref={bottomRef} />
      {cardEvents.length === 0 && (
        <p className="secondary cc-thread-empty">{t("cc.threadIdle")}</p>
      )}
    </div>
  );
}

/** turns 已渲染 user/assistant 气泡 —— 线程里跳过重复的这两类。 */
function isTurnDuplicate(event: CommandEvent): boolean {
  return event.event_type === "user_message" || event.event_type === "assistant_message";
}

function EventCard({ event, sessionId }: { event: CommandEvent; sessionId: string }) {
  switch (event.event_type) {
    case "plan_created":
      return <PlanCard event={event} />;
    case "tool_call":
      return <ToolCard event={event} />;
    case "tool_result":
      return <ToolResultCard event={event} />;
    case "tool_error":
      return <ToolErrorCard event={event} />;
    case "confirmation_requested":
    case "confirmation_decided":
      return <ConfirmationCard event={event} sessionId={sessionId} />;
    case "task_started":
    case "task_progress":
    case "task_completed":
    case "task_failed":
      return <TaskCard event={event} />;
    case "run_completed":
    case "run_failed":
      return <RunResultCard event={event} />;
    case "artifact_created":
      return <ArtifactCard event={event} />;
    case "memory_compacted":
      return <MemoryCard event={event} />;
    case "step_started":
    case "step_updated":
    case "session_created":
    case "user_message":
    case "assistant_message":
      return null; // 由计划链/气泡/静默呈现
    default:
      return null;
  }
}

function CardShell({
  kind,
  title,
  testid,
  tone,
  children,
}: {
  kind: string;
  title: string;
  testid: string;
  tone?: "ok" | "error" | "running";
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`cc-card cc-card-${kind}${tone ? ` cc-card-${tone}` : ""}`}
      data-testid={testid}
      role="status"
    >
      <span className="cc-card-kind mono">{title}</span>
      {children}
    </div>
  );
}

function PlanCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  const steps = (event.payload?.steps as Array<{ title?: string }>) ?? [];
  return (
    <CardShell kind="plan" title={t("cc.cardPlan")} testid="card-plan">
      <span className="cc-card-title">{String(event.payload?.title ?? "")}</span>
      {steps.length > 0 && (
        <span className="secondary">
          {steps.map((s) => s.title).filter(Boolean).join(" → ")}
        </span>
      )}
    </CardShell>
  );
}

function ToolCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  return (
    <CardShell kind="tool" title={t("cc.cardToolCall")} testid="card-tool-call" tone="running">
      <span className="cc-card-title mono">{String(event.payload?.tool ?? "")}</span>
    </CardShell>
  );
}

function ToolResultCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  const detail = String(event.payload?.detail ?? "");
  return (
    <CardShell kind="tool-result" title={t("cc.cardToolResult")} testid="card-tool-result" tone="ok">
      <span className="cc-card-title mono">{String(event.payload?.tool ?? "")}</span>
      {detail && <span className="secondary">{detail}</span>}
      {(event.artifact_ids ?? []).length > 0 && (
        <span className="secondary mono">{event.artifact_ids.join(" · ")}</span>
      )}
    </CardShell>
  );
}

function ToolErrorCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  return (
    <CardShell kind="tool-error" title={t("cc.cardToolError")} testid="card-tool-error" tone="error">
      <span className="cc-card-title mono">{String(event.payload?.tool ?? "")}</span>
      <span className="status-error">{String(event.payload?.error ?? "")}</span>
    </CardShell>
  );
}

function ConfirmationCard({ event, sessionId }: { event: CommandEvent; sessionId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isRequest = event.event_type === "confirmation_requested";
  const status = String(event.status ?? "pending");
  const tool = String(event.payload?.tool ?? "");

  const decideMutation = useMutation({
    mutationFn: async (decision: "approved" | "rejected") => {
      const resp = await fetch("/api/v1/command/confirmations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: tool,
          arguments: (event.payload?.arguments as Record<string, unknown>) ?? {},
          command_session_id: sessionId,
        }),
      });
      if (!resp.ok) throw new Error("confirmation.create_failed");
      const created = (await resp.json()) as { confirmation: { confirmation_id: string } };
      const decide = await fetch(
        `/api/v1/command/confirmations/${created.confirmation.confirmation_id}/decide`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision }) },
      );
      if (!decide.ok) throw new Error("confirmation.decide_failed");
      return decide.json();
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cc-events", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["cc-confirmations-pending"] });
    },
  });

  if (!isRequest) {
    return (
      <CardShell
        kind="confirmation"
        title={t("cc.cardConfirmation")}
        testid="card-confirmation-decided"
        tone={status === "approved" ? "ok" : status === "rejected" ? "error" : undefined}
      >
        <span className="cc-card-title mono">{tool}</span>
        <span className="secondary">{t(`cc.confirmationStatus.${status}`, { defaultValue: status })}</span>
      </CardShell>
    );
  }

  return (
    <CardShell kind="confirmation" title={t("cc.cardConfirmation")} testid="card-confirmation">
      <span className="cc-card-title mono">{tool}</span>
      <span className="secondary mono cc-card-digest">
        {String(event.payload?.arguments_digest ?? "").slice(0, 12)}
      </span>
      <div className="cc-card-actions">
        <button
          type="button"
          className="gl-button gl-button-primary"
          data-testid="confirmation-approve"
          aria-label={t("cc.confirmApprove")}
          disabled={decideMutation.isPending}
          onClick={() => decideMutation.mutate("approved")}
        >
          {t("cc.confirmApprove")}
        </button>
        <button
          type="button"
          className="gl-button gl-button-ghost"
          data-testid="confirmation-reject"
          aria-label={t("cc.confirmReject")}
          disabled={decideMutation.isPending}
          onClick={() => decideMutation.mutate("rejected")}
        >
          {t("cc.confirmReject")}
        </button>
      </div>
    </CardShell>
  );
}

function TaskCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  const status = String(event.status ?? event.event_type.replace("task_", ""));
  const progress = Number(event.payload?.progress ?? 0);
  return (
    <CardShell
      kind="task"
      title={t("cc.cardTask")}
      testid={`card-task-${status}`}
      tone={status === "succeeded" ? "ok" : status === "failed" ? "error" : "running"}
    >
      <span className="cc-card-title mono">{String(event.payload?.tool ?? "")}</span>
      <span className="secondary">
        {t(`cc.taskStatus.${status}`, { defaultValue: status })}
        {progress > 0 ? ` · ${progress}%` : ""}
      </span>
    </CardShell>
  );
}

function RunResultCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  const failed = event.event_type === "run_failed";
  return (
    <CardShell
      kind="run"
      title={t("cc.cardRun")}
      testid={failed ? "card-run-failed" : "card-run-completed"}
      tone={failed ? "error" : "ok"}
    >
      <span className="cc-card-title">
        {failed
          ? `${t("commander.planFailed")}: ${String(event.payload?.failed_step ?? "")}`
          : t("commander.planCompleted")}
      </span>
    </CardShell>
  );
}

function ArtifactCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  return (
    <CardShell kind="artifact" title={t("cc.cardArtifact")} testid="card-artifact">
      <span className="secondary mono">{(event.artifact_ids ?? []).join(" · ")}</span>
      <span className="secondary">{t("cc.cardArtifactNote")}</span>
    </CardShell>
  );
}

function MemoryCard({ event }: { event: CommandEvent }) {
  const { t } = useTranslation();
  return (
    <CardShell kind="memory" title={t("cc.cardMemory")} testid="card-memory">
      <span className="secondary">
        {t("cc.memoryCompacted", { version: String(event.payload?.summary_version ?? "") })}
      </span>
    </CardShell>
  );
}
