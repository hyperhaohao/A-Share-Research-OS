/**
 * 经验卡工作台数据契约（Guanlan Direct Port G3，方案 §14/§24）。
 * GET /views/experience/{card_id} 一次装配：原（主张/证据原文 + cite 序号）/
 * 炼（卡字段）/ 验（验证记录）/ 用（已批准知识库）。
 */

export interface CardValidation {
  validation_id: string;
  method: string;
  summary: string;
  created_at: string | null;
}

export interface ExperienceCardDetail {
  card_id: string;
  instrument_id: string;
  title: string | null;
  status: string;
  category?: string | null;
  statement: string;
  mechanism: string;
  applicable_conditions: string[];
  invalid_conditions: string[];
  source_report_id: string;
  source_claim_ids: string[];
  source_evidence_ids: string[];
  current_version: number;
  refine_method: string;
  confidence: number;
  verdict: string | null;
  quant_expression?: string | null;
  versions: Array<{ version_no: number; method: string; created_at: string | null }>;
  validations: CardValidation[];
  created_at: string | null;
}

export interface SourceClaim {
  claim_id: string;
  cite: number;
  statement: string;
  claim_type: string;
  fact_status: string;
  confidence: number;
  evidence_refs: string[];
}

export interface SourceEvidence {
  evidence_id: string;
  summary: string;
  source: string;
  authority_level: string;
  fact_status: string;
  available_time: string | null;
}

export interface ExperienceView {
  card: ExperienceCardDetail;
  source: {
    report_id: string;
    report_version_id: string | null;
    claims: SourceClaim[];
    evidence: SourceEvidence[];
  };
  kb: Array<{
    card_id: string;
    title: string | null;
    category: string | null;
    confidence: number;
    verdict: string | null;
    quant_expression: string | null;
    updated_at: string | null;
  }>;
}

export async function fetchExperienceView(cardId: string): Promise<ExperienceView> {
  const resp = await fetch(`/api/v1/views/experience/${encodeURIComponent(cardId)}`);
  if (!resp.ok) throw new Error("experience.not_found");
  return ((await resp.json()) as { view: ExperienceView }).view;
}
