/**
 * Command Center — ResearchPlan 前端投影（donor chat 多会话/工具链行为的
 * ASRO 数据源：/command/sessions + /views/command-center，方案 §6）。
 * 计划步骤 → G0 ResearchStep 三态映射在此唯一归口。
 */

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

import type { ResearchStepStatus } from "../../ui/guanlan";

/** ASRO 计划步骤状态 → donor 墨痕三态（done/running/pending）。 */
export function stepToInkStatus(status: string): ResearchStepStatus {
  if (status === "ok") return "done";
  if (status === "running") return "running";
  return "pending";
}

/** 步骤序号 → donor 墨痕的 mono 步号（01 / 02 …）。 */
export function stepIndex(i: number): string {
  return String(i + 1).padStart(2, "0");
}
