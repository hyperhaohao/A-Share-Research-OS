/**
 * Workflow Studio 节点目录（Guanlan Direct Port G4，方案 §15/§35）。
 * 目录与 ASRO 执行器强对应（backend NODE_KINDS）：能执行什么，目录就有什么。
 * donor 25 类目录中未接引擎的部分不伪造（方案 §25）。
 */

export type ParamType = "text" | "number" | "select";

export interface ParamSpec {
  id: string;
  labelKey: string;
  type: ParamType;
  defaultValue: string | number;
  min?: number;
  max?: number;
  options?: Array<{ value: string; labelKey: string }>;
  hintKey?: string;
  optional?: boolean;
}

export interface KindSpec {
  kind: string;
  titleKey: string;
  descKey: string;
  color: string;
  params: ParamSpec[];
}

export const NODE_SPECS: Record<string, KindSpec> = {
  data: {
    kind: "data",
    titleKey: "studio.kind.data",
    descKey: "studio.kindDesc.data",
    color: "var(--color-info)",
    params: [
      {
        id: "instrument_id",
        labelKey: "studio.param.instrument",
        type: "text",
        defaultValue: "",
        hintKey: "studio.hint.instrument",
        optional: true,
      },
      { id: "limit", labelKey: "studio.param.bars", type: "number", defaultValue: 1200, min: 20, max: 5000 },
    ],
  },
  rule: {
    kind: "rule",
    titleKey: "studio.kind.rule",
    descKey: "studio.kindDesc.rule",
    color: "var(--color-warning)",
    params: [
      { id: "horizon_days", labelKey: "studio.param.horizon", type: "number", defaultValue: 20, min: 1, max: 250 },
      { id: "threshold_pct", labelKey: "studio.param.threshold", type: "number", defaultValue: 0, min: -100, max: 100 },
    ],
  },
  expression: {
    kind: "expression",
    titleKey: "studio.kind.expression",
    descKey: "studio.kindDesc.expression",
    color: "#7c5cbf",
    params: [
      {
        id: "expr",
        labelKey: "studio.param.expr",
        type: "text",
        defaultValue: "",
        hintKey: "studio.hint.expr",
      },
    ],
  },
  validation: {
    kind: "validation",
    titleKey: "studio.kind.validation",
    descKey: "studio.kindDesc.validation",
    color: "var(--color-positive)",
    params: [],
  },
  output: {
    kind: "output",
    titleKey: "studio.kind.output",
    descKey: "studio.kindDesc.output",
    color: "var(--color-accent)",
    params: [
      {
        id: "card_id",
        labelKey: "studio.param.card",
        type: "text",
        defaultValue: "",
        hintKey: "studio.hint.card",
        optional: true,
      },
    ],
  },
};

/** Palette 分组（donor CATALOG 分组习语，按研究阶段） */
export const NODE_CATALOG: Array<{ groupKey: string; kinds: string[] }> = [
  { groupKey: "studio.group.input", kinds: ["data"] },
  { groupKey: "studio.group.rule", kinds: ["rule", "expression"] },
  { groupKey: "studio.group.evaluate", kinds: ["validation"] },
  { groupKey: "studio.group.persist", kinds: ["output"] },
];

export function defaultParams(kind: string): Record<string, string | number> {
  const spec = NODE_SPECS[kind];
  const out: Record<string, string | number> = {};
  if (spec) for (const p of spec.params) out[p.id] = p.defaultValue;
  return out;
}

/** 编辑器图模型（与后端 API 同形） */
export interface DefNode {
  key: string;
  kind: string;
  title: string | null;
  params: Record<string, string | number>;
}

export interface DefEdge {
  from: string;
  to: string;
}

export interface DefinitionSummary {
  def_id: string;
  name: string;
  instrument_id: string | null;
  current_version: number;
  updated_at: string | null;
}

export interface Definition extends DefinitionSummary {
  nodes: DefNode[];
  edges: DefEdge[];
  versions: Array<{ version_no: number; note: string | null; created_at: string | null }>;
}

export function validateGraphClient(nodes: DefNode[], edges: DefEdge[]): string | null {
  if (nodes.length === 0) return "studio.err.empty";
  const kinds = nodes.map((n) => n.kind);
  if (!kinds.includes("data")) return "studio.err.noData";
  if (kinds.filter((k) => k === "output").length !== 1) return "studio.err.outputCount";
  const keys = new Set(nodes.map((n) => n.key));
  for (const e of edges) {
    if (!keys.has(e.from) || !keys.has(e.to)) return "studio.err.danglingEdge";
  }
  return null;
}
