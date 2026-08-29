import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CommandPlanSteps, type Plan } from "./CommandPlanSteps";
import { uiLang } from "../presentation/enumLabels";
import { formatWhen } from "../presentation/format";

interface Turn {
  turn_id: string;
  role: string;
  text: string;
  plan_id: string | null;
  created_at: string | null;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok && resp.status !== 202) throw new Error("network.unreachable");
  return resp.json();
}

/**
 * 中栏对话（总纲 §38/§41）：一句话下达研究指令 → 结构化计划 → 执行过程
 * 就地显示。重要产物走 Artifact/计划对象，对话只是入口，不是仓库。
 */
export function ConversationPanel({
  sessionId,
  activePlan,
}: {
  sessionId: string | null;
  activePlan: Plan | null;
}) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const detailQuery = useQuery({
    queryKey: ["command-session", sessionId],
    enabled: sessionId != null,
    refetchInterval: activePlan?.status === "running" ? 1500 : 5000,
    queryFn: () =>
      fetchJson<{ session: unknown; turns: Turn[]; plans: Plan[] }>(
        `/api/v1/command/sessions/${sessionId}`,
      ),
  });

  const turns = detailQuery.data?.turns ?? [];

  useEffect(() => {
    // jsdom (unit tests) does not implement scrollIntoView
    bottomRef.current?.scrollIntoView?.({ block: "end" });
  }, [turns.length, activePlan?.status]);

  const sendMutation = useMutation({
    mutationFn: async () => {
      const body = JSON.stringify({ text });
      setText("");
      return fetchJson<{ plan: Plan | null }>(
        `/api/v1/command/sessions/${sessionId}/turns`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body },
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["command-session", sessionId] }),
    onError: () => queryClient.invalidateQueries({ queryKey: ["command-session", sessionId] }),
  });

  return (
    <section className="card conversation-panel" data-testid="commander-conversation">
      <h2>{t("commander.conversation")}</h2>
      <div className="conversation-turns">
        {turns.length === 0 && (
          <p className="secondary">{t("commander.inputHint")}</p>
        )}
        {turns.map((turn) => (
          <div
            key={turn.turn_id}
            className={`turn-bubble ${turn.role}`}
            data-testid={turn.role === "commander" ? "commander-reply" : undefined}
          >
            <span className="turn-text">{turn.text}</span>
            <span className="turn-time secondary">{formatWhen(turn.created_at, lang)}</span>
          </div>
        ))}
        {activePlan && activePlan.status === "running" && (
          <CommandPlanSteps plan={activePlan} compact data-testid="commander-plan-progress" />
        )}
        <div ref={bottomRef} />
      </div>
      <form
        className="conversation-input"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim() && !sendMutation.isPending) sendMutation.mutate();
        }}
      >
        <input
          className="control-input"
          data-testid="commander-input"
          value={text}
          placeholder={t("commander.inputPlaceholder")}
          aria-label={t("commander.conversation")}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          type="submit"
          className="control-btn"
          data-testid="commander-send"
          disabled={sendMutation.isPending || !text.trim()}
        >
          {t("commander.send")}
        </button>
      </form>
      {activePlan && activePlan.status !== "running" && (
        <div className="plan-result">
          <CommandPlanSteps plan={activePlan} compact data-testid="commander-plan-progress" />
        </div>
      )}
    </section>
  );
}

export function useEnsureSession(): [string | null, (id: string) => void] {
  const { data } = useQuery({
    queryKey: ["command-sessions"],
    queryFn: async (): Promise<string | null> => {
      const resp = await fetch("/api/v1/command/sessions?limit=1");
      if (!resp.ok) return null;
      const body = (await resp.json()) as { results: Array<{ session_id: string }> };
      if (body.results.length > 0) return body.results[0].session_id;
      const created = await fetchJson<{ session: { session_id: string } }>(
        "/api/v1/command/sessions",
        { method: "POST" },
      );
      return created.session.session_id;
    },
    staleTime: Infinity,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);
  useEffect(() => {
    if (data && !sessionId) setSessionId(data);
  }, [data, sessionId]);
  return [sessionId, setSessionId];
}

export type { Turn };
