/**
 * Guanlan Direct Port — MarketTicker（donor ui/_shared/shared.jsx MarketTicker → TSX）。
 * 市况条：名称 + 现值 + 涨跌 delta（负值跌色，其余涨色 —— donor 原逻辑）。
 * 数据由调用方从真实行情组装（G1 中枢头部/G8 宏观），组件不做任何取数。
 */

export interface TickerItem {
  name: string;
  value: string;
  delta?: string;
}

export function MarketTicker({ items }: { items: TickerItem[] }) {
  return (
    <div className="gl-ticker">
      {items.map((it, i) => (
        <div key={i} className="gl-ticker-item">
          <span className="gl-ticker-name">{it.name}</span>
          <span className="gl-ticker-value num">{it.value}</span>
          {it.delta && <span className={it.delta.startsWith("-") ? "down num" : "up num"}>{it.delta}</span>}
        </div>
      ))}
    </div>
  );
}
