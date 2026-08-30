/**
 * Guanlan Direct Port — Sparkline（donor ui/_shared/shared.jsx → TSX，方案 §5/§31）。
 * 免图表库 SVG 迷你走势；涨用 --zhu（CN 涨=红），跌用 --dai。
 * 真实数据由调用方传入；无数据返回 null（方案 §25：无数据显形为空，不造假图）。
 */

export interface SparklineProps {
  data: number[];
  w?: number;
  h?: number;
  up?: boolean;
  fill?: boolean;
}

export function Sparkline({ data, w = 120, h = 36, up = true, fill = true }: SparklineProps) {
  if (!data || data.length < 2) {
    return null;
  }
  const max = Math.max(...data);
  const min = Math.min(...data);
  const dx = w / (data.length - 1);
  const y = (v: number) => h - ((v - min) / (max - min || 1)) * h;
  const points = data.map((v, i) => `${i * dx},${y(v)}`).join(" ");
  const color = up ? "var(--zhu)" : "var(--dai)";
  return (
    <svg width={w} height={h} style={{ display: "block" }} role="img">
      {fill && <polygon points={`0,${h} ${points} ${w},${h}`} fill={color} opacity="0.12" />}
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.4" />
    </svg>
  );
}
