import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Panel } from "../../ui/guanlan";
import { formatWhen } from "../../presentation/format";
import { uiLang } from "../../presentation/enumLabels";

/**
 * Replay（Guanlan Direct Port G7，方案 §18）：
 * 观察→信号→决策 的合并时序回放 —— 滑块推进到任一时刻，
 * 显示「截至该步」已出现的记录（三分离记录回放，非事件流伪造）。
 */

export interface ReplayRecord {
  id: string;
  kind: "observation" | "signal" | "decision";
  at: string | null;
  text: string;
}

const KIND_LABEL: Record<ReplayRecord["kind"], string> = {
  observation: "monitorWs.kind.observation",
  signal: "monitorWs.kind.signal",
  decision: "monitorWs.kind.decision",
};

export function MonitorReplay({ records }: { records: ReplayRecord[] }) {
  const { t, i18n } = useTranslation();
  const lang = uiLang(i18n.language);
  const sorted = useMemo(
    () =>
      [...records].sort((a, b) => String(a.at ?? "").localeCompare(String(b.at ?? ""))),
    [records],
  );
  const [idx, setIdx] = useState(sorted.length);
  const shown = sorted.slice(0, Math.min(idx, sorted.length));
  const position = Math.min(idx, sorted.length);

  if (sorted.length === 0) {
    return (
      <Panel title={t("monitorWs.replayTitle")}>
        <p className="secondary">{t("monitorWs.replayEmpty")}</p>
      </Panel>
    );
  }

  return (
    <Panel title={t("monitorWs.replayTitle")} hint={t("monitorWs.replayHint")}>
      <div className="sm-replay" data-testid="monitor-replay">
        <input
          type="range"
          className="sm-replay-slider"
          min={0}
          max={sorted.length}
          value={position}
          aria-label={t("monitorWs.replayTitle")}
          onChange={(e) => setIdx(Number(e.target.value))}
        />
        <div className="sm-replay-counter mono">
          {position} / {sorted.length}
        </div>
        <ul className="watch-list sm-replay-list">
          {shown.map((r) => (
            <li key={r.id} className="result-row">
              <span className={`sm-replay-kind sm-kind-${r.kind}`}>
                {t(KIND_LABEL[r.kind])}
              </span>
              <span className="sm-replay-text">{r.text}</span>
              <span className="secondary mono">{formatWhen(r.at, lang)}</span>
            </li>
          ))}
          {shown.length === 0 && (
            <li className="secondary">{t("monitorWs.replayStart")}</li>
          )}
        </ul>
      </div>
    </Panel>
  );
}
