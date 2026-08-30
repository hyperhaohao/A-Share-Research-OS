import { describe, expect, it } from "vitest";
import {
  NODE_CATALOG,
  NODE_SPECS,
  defaultParams,
  validateGraphClient,
  type DefEdge,
  type DefNode,
} from "../src/features/workflow-studio/spec";

describe("Workflow Studio — node catalog (方案 §15)", () => {
  it("catalog covers exactly the executable kinds, grouped", () => {
    const catalogKinds = NODE_CATALOG.flatMap((g) => g.kinds).sort();
    expect(catalogKinds).toEqual(Object.keys(NODE_SPECS).sort());
    expect(catalogKinds).toEqual(["data", "expression", "output", "rule", "validation"]);
  });

  it("every param has defaults and localized label keys", () => {
    for (const spec of Object.values(NODE_SPECS)) {
      for (const p of spec.params) {
        expect(p.defaultValue).toBeDefined();
        expect(p.labelKey).toMatch(/^studio\.param\./);
      }
    }
    expect(defaultParams("rule")).toEqual({ horizon_days: 20, threshold_pct: 0 });
  });
});

describe("Workflow Studio — client graph validation", () => {
  const node = (key: string, kind: string): DefNode => ({ key, kind, title: null, params: {} });

  it("rejects empty / data-less / multi-output graphs", () => {
    expect(validateGraphClient([], [])).toBe("studio.err.empty");
    expect(
      validateGraphClient([node("r", "rule"), node("o", "output")], [{ from: "r", to: "o" }]),
    ).toBe("studio.err.noData");
    expect(
      validateGraphClient(
        [node("d", "data"), node("o1", "output"), node("o2", "output")],
        [],
      ),
    ).toBe("studio.err.outputCount");
  });

  it("accepts a well-formed graph and rejects dangling edges", () => {
    const nodes = [node("d", "data"), node("r", "rule"), node("o", "output")];
    const edges: DefEdge[] = [
      { from: "d", to: "r" },
      { from: "r", to: "o" },
    ];
    expect(validateGraphClient(nodes, edges)).toBeNull();
    expect(validateGraphClient(nodes, [{ from: "d", to: "ghost" }])).toBe(
      "studio.err.danglingEdge",
    );
  });
});
