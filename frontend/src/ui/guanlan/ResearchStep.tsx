/**
 * Guanlan Direct Port — ResearchStep（donor ui/_shared/shared.jsx ResearchStep → TSX）。
 * 研究步骤墨痕行：done（墨点）/ running（印章红脉冲）/ pending（空圈）。
 * G1 中枢左栏计划区即由它驱动（donor 原型亮点的 TSX 化）。
 */

export type ResearchStepStatus = "done" | "running" | "pending";

export interface ResearchStepProps {
  step: string;
  label: string;
  status: ResearchStepStatus;
  time?: string;
}

export function ResearchStep({ step, label, status, time }: ResearchStepProps) {
  return (
    <div className="gl-research-step" data-status={status}>
      <div className="gl-step-marker">
        <div className="gl-step-marker-dot" />
        {status === "running" && <div className="gl-step-marker-ring" />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span className="gl-step-index">{step}</span>
          <span className="gl-step-label">{label}</span>
        </div>
      </div>
      {time && <span className="gl-step-time">{time}</span>}
    </div>
  );
}
