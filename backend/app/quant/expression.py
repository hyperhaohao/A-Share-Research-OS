"""Deterministic quant-expression parser (V2 深度扩展 c).

经验卡的量化规则自由表达 —— 受约束的确定式 DSL，绝不用 eval：

    avg_return > 0 AND hit_rate >= 55 AND worst_return > -10

    指标: avg_return | hit_rate | worst_return | best_return
    比较: >= <= > < (数值可为负/小数)
    组合: AND（v1）
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_METRICS = {
    "avg_return": "avg_return_pct",
    "hit_rate": "hit_rate_pct",
    "worst_return": "worst_return_pct",
    "best_return": "best_return_pct",
}
_OPS = (">=", "<=", ">", "<")
_COMPARISON_RE = re.compile(
    r"^\s*(" + "|".join(_METRICS) + r")\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*$"
)


class ExpressionError(ValueError):
    """Parse failure — the user gets the reason, never a silent guess."""


@dataclass(frozen=True)
class Comparison:
    metric: str      # canonical metric key (avg_return_pct …)
    op: str
    value: float

    def evaluate(self, metrics: dict) -> bool:
        actual = metrics.get(self.metric)
        if actual is None:
            return False
        if self.op == ">=":
            return actual >= self.value
        if self.op == "<=":
            return actual <= self.value
        if self.op == ">":
            return actual > self.value
        return actual < self.value


@dataclass(frozen=True)
class Expression:
    comparisons: tuple[Comparison, ...]

    def evaluate(self, metrics: dict) -> tuple[bool, str]:
        """All comparisons must hold (AND); returns (verdict, readable reason)."""
        failed: list[str] = []
        for comp in self.comparisons:
            actual = metrics.get(comp.metric)
            ok = comp.evaluate(metrics)
            mark = "✓" if ok else "✗"
            detail = f"{mark} {comp.metric}={actual} {comp.op} {comp.value}"
            if not ok:
                failed.append(detail)
        if failed:
            return False, "；".join(failed)
        return True, "全部条件满足：" + "；".join(
            f"{c.metric}={metrics.get(c.metric)} {c.op} {c.value}" for c in self.comparisons
        )


def parse_quant_expression(text: str) -> Expression:
    """Parse the constrained grammar; raise ExpressionError with the reason."""
    text = (text or "").strip()
    if not text:
        raise ExpressionError("empty expression")
    clauses = [c.strip() for c in text.split("AND")]
    comparisons: list[Comparison] = []
    for clause in clauses:
        match = _COMPARISON_RE.match(clause)
        if match is None:
            raise ExpressionError(f"无法解析子句：{clause!r}（格式：指标 比较符 数值）")
        metric_key, op, value = match.groups()
        comparisons.append(Comparison(metric=_METRICS[metric_key], op=op, value=float(value)))
    if not comparisons:
        raise ExpressionError("empty expression")
    return Expression(comparisons=tuple(comparisons))
