import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Candles, Panel } from "../../ui/guanlan";

/**
 * K线区（Guanlan Direct Port G7，方案 §18；G0 Candles 复用）：
 * 证据层真实日线（/market-data/daily-bars，PIT 可见）；信号日期在 K 线范围内
 * → 底部信号条对位标记。无 K 线数据 → 显形「暂无」（不画假图，方案 §25）。
 */

interface Bar {
  date: string;
  open?: number;
  close: number;
  high?: number;
  low?: number;
}

export interface SignalMark {
  label: string;
  at: string | null;
  positive: boolean;
}

export function MonitorCandles({
  instrumentId,
  signals,
}: {
  instrumentId: string;
  signals: SignalMark[];
}) {
  const { t } = useTranslation();
  const barsQuery = useQuery({
    queryKey: ["monitor-bars", instrumentId],
    enabled: instrumentId !== "",
    staleTime: 60_000,
    queryFn: async () => {
      const resp = await fetch(
        `/api/v1/market-data/daily-bars?instrument=${encodeURIComponent(instrumentId)}&limit=60`,
      );
      if (!resp.ok) throw new Error("network.unreachable");
      return (await resp.json()) as {
        has_data: boolean;
        bars: Bar[];
        total_collected: number;
      };
    },
  });

  const bars = barsQuery.data?.bars ?? [];
  const candleData = bars
    .filter((b) => typeof b.close === "number")
    .map((b) => ({
      o: b.open ?? b.close,
      c: b.close,
      h: b.high ?? b.close,
      l: b.low ?? b.close,
    }));

  const firstDate = bars[0]?.date ?? "";
  const lastDate = bars[bars.length - 1]?.date ?? "";
  const marks = signals
    .map((s) => {
      const day = (s.at ?? "").slice(0, 10);
      const idx = bars.findIndex((b) => b.date === day);
      return { ...s, idx };
    })
    .filter((m) => m.idx >= 0);

  return (
    <Panel title={t("monitorWs.candlesTitle")} hint={t("monitorWs.candlesHint")}>
      <div data-testid="monitor-candles">
        {candleData.length >= 2 ? (
          <>
            <Candles data={candleData} w={640} h={180} />
            <div className="sm-signal-strip">
              {marks.map((m, i) => (
                <span
                  key={i}
                  className={`sm-signal-mark ${m.positive ? "up" : "down"}`}
                  style={{ left: `${(m.idx / Math.max(candleData.length - 1, 1)) * 100}%` }}
                  title={`${m.at ?? ""} ${m.label}`}
                >
                  ▲
                </span>
              ))}
            </div>
            <p className="secondary mono sm-dates">
              {firstDate} → {lastDate} · {candleData.length} {t("monitorWs.barsUnit")}
            </p>
          </>
        ) : (
          <p className="secondary" data-testid="monitor-candles-empty">
            {t("monitorWs.noBars")}
          </p>
        )}
      </div>
    </Panel>
  );
}
