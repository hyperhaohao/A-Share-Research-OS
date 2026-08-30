/**
 * Guanlan Direct Port — Candles（donor ui/_shared/shared.jsx Candles → TSX）。
 * 免图表库 SVG K 线；G7 策略盯盘复用为页面级 K 线组件的底座。
 * 无数据返回 null（方案 §25：不造假图）。
 */

export interface CandleDatum {
  o: number;
  c: number;
  h: number;
  l: number;
}

export interface CandlesProps {
  data: CandleDatum[];
  w?: number;
  h?: number;
}

export function Candles({ data, w = 360, h = 140 }: CandlesProps) {
  if (!data || data.length === 0) {
    return null;
  }
  const all = data.flatMap((d) => [d.h, d.l]);
  const max = Math.max(...all);
  const min = Math.min(...all);
  const pad = 6;
  const cw = (w - pad * 2) / data.length;
  const bw = cw * 0.6;
  const y = (v: number) => pad + ((max - v) / (max - min || 1)) * (h - pad * 2);
  return (
    <svg width={w} height={h} style={{ display: "block" }} role="img">
      {[0.25, 0.5, 0.75].map((t) => (
        <line
          key={t}
          x1={0}
          x2={w}
          y1={pad + t * (h - pad * 2)}
          y2={pad + t * (h - pad * 2)}
          stroke="var(--line-soft)"
          strokeDasharray="2 3"
        />
      ))}
      {data.map((d, i) => {
        const isUp = d.c >= d.o;
        const color = isUp ? "var(--zhu)" : "var(--dai)";
        const x = pad + i * cw + (cw - bw) / 2;
        const cx = pad + i * cw + cw / 2;
        const yo = y(d.o);
        const yc = y(d.c);
        const yh = y(d.h);
        const yl = y(d.l);
        const top = Math.min(yo, yc);
        const bh = Math.max(1, Math.abs(yo - yc));
        return (
          <g key={i}>
            <line x1={cx} x2={cx} y1={yh} y2={yl} stroke={color} strokeWidth="1" />
            <rect x={x} y={top} width={bw} height={bh} fill={color} />
          </g>
        );
      })}
    </svg>
  );
}
