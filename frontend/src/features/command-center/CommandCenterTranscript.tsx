import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ResearchStep } from "../../ui/guanlan";
import { uiLang } from "../../presentation/enumLabels";
import { formatWhen } from "../../presentation/format";
import { useInstrumentName } from "../../shared/instrument";
import { stepIndex, stepToInkStatus, type Plan } from "./plan";
import { EventThread } from "./EventThread";

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
 * 中栏对话（donor Transcript 行为 → ASRO 数据，方案 §6）：
 * 用户气泡 / 指挥官回复 / 计划执行链就地展开（墨痕行，donor 工具链等价物）/
 * 上下文 chip 的 Composer。重要产物走 Artifact/计划对象，对话只是入口。
 */
export function CommandCenterTranscript({
  sessionId,
  activePlan,
  contextInstrument,
}: {
  sessionId: string | null;
  activePlan: Plan | null;
  contextInstrument: string | null;
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
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["command-session", sessionId] }),
    onError: () =>
      queryClient.invalidateQueries({ queryKey: ["command-session", sessionId] }),
  });

  const planById = new Map((detailQuery.data?.plans ?? []).map((p) => [p.plan_id, p]));

  return (
    <section
      className="card conversation-panel"
      data-testid="commander-conversation"
    >
      <h2>{t("commander.conversation")}</h2>
      <div className="conversation-turns">
        {turns.length === 0 && (
          <p className="secondary">{t("commander.inputHint")}</p>
        )}
        {turns.map((turn) => (
          <div key={turn.turn_id}>
            <div
              className={`turn-bubble ${turn.role}`}
              data-testid={turn.role === "commander" ? "commander-reply" : undefined}
            >
              <span className="turn-text">{turn.text}</span>
              <span className="turn-time secondary">
                {formatWhen(turn.created_at, lang)}
              </span>
            </div>
            {turn.plan_id && planById.has(turn.plan_id) && (
              <PlanChain plan={planById.get(turn.plan_id)!} />
            )}
          </div>
        ))}
        {activePlan && activePlan.status === "running" && (
          <PlanChain plan={activePlan} testid="commander-plan-progress" />
        )}
        {activePlan && activePlan.status !== "running" && (
          <div className="plan-result">
            <PlanChain plan={activePlan} testid="commander-plan-progress" />
          </div>
        )}
        {/* F10：事件线程卡片（工具/审批/任务/产物/错误 —— §8.10 中栏） */}
        {sessionId != null && <EventThread sessionId={sessionId} />}
        <div ref={bottomRef} />
      </div>
      <form
        className="conversation-input"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim() && !sendMutation.isPending) sendMutation.mutate();
        }}
      >
        {contextInstrument && <ContextChip instrumentId={contextInstrument} />}
        <div className="cc-composer-row">
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
            className="gl-button gl-button-primary"
            data-testid="commander-send"
            disabled={sendMutation.isPending || !text.trim()}
          >
            {t("commander.send")}
          </button>
        </div>
      </form>
    </section>
  );
}

/** 计划执行链（donor ToolChain 等价物）：墨痕行 + 完成态折叠在对话流里。 */
function PlanChain({
  plan,
  testid,
}: {
  plan: Plan;
  testid?: string;
}) {
  const { t } = useTranslation();
  return (
    <div className="cc-plan-chain" data-testid={testid}>
      {plan.steps.map((step, i) => (
        <ResearchStep
          key={step.step_id}
          step={stepIndex(i)}
          label={step.title}
          status={stepToInkStatus(step.status)}
        />
      ))}
      {plan.status === "completed" && (
        <p className="status-ok cc-chain-done">{t("commander.planCompleted")}</p>
      )}
      {plan.status === "failed" && (
        <p className="status-error cc-chain-done">
          {t("commander.planFailed")}: {plan.error}
        </p>
      )}
    </div>
  );
}

/** 上下文 chip（donor Composer context chip）：当前研究上下文，不要求重复输入标的。 */
function ContextChip({ instrumentId }: { instrumentId: string }) {
  const { t } = useTranslation();
  const profile = useInstrumentName(instrumentId);
  return (
    <span className="cc-context-chip" data-testid="commander-context-chip">
      <span className="seal" style={{ width: 14, height: 14, fontSize: 9 }}>
        {t("guanlan.brandSeal")}
      </span>
      {profile?.name ?? instrumentId}
      <span className="secondary">{t("cc.contextChip")}</span>
    </span>
  );
}

