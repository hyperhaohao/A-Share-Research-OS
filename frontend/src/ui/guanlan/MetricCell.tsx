/**
 * Guanlan Direct Port — MetricCell（donor ui/_shared/shared.jsx MetricCell → TSX）。
 * 数据小卡：标签 + 等宽大数字 + 单位 + 涨跌 delta。数值由调用方组装。
 */

export interface MetricCellProps {
  label: string;
  value: string;
  delta?: string;
  unit?: string;
}

export function MetricCell({ label, value, delta, unit }: MetricCellProps) {
  return (
    <div className="gl-metric-cell">
      <div className="gl-metric-label">{label}</div>
      <div className="gl-metric-value-row">
        <span className="gl-metric-value">{value}</span>
        {unit && <span className="gl-metric-unit">{unit}</span>}
      </div>
      {delta && <div className={`gl-metric-delta ${delta.startsWith("-") ? "down" : "up"}`}>{delta}</div>}
    </div>
  );
}
