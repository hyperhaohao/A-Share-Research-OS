/**
 * Instrument identity 读取 hook（PW0：所有入口共用同一身份路径）。
 * 各页面不得自建 instrument fetch —— 名称/代码一律经此 hook（缓存共享）。
 */

import { useQuery } from "@tanstack/react-query";

export interface InstrumentNameProfile {
  name: string;
  code: string;
}

export function useInstrumentName(instrumentId: string | null | undefined) {
  const { data } = useQuery({
    queryKey: ["instrument", instrumentId],
    enabled: instrumentId != null && instrumentId !== "",
    staleTime: 60000,
    queryFn: async (): Promise<InstrumentNameProfile | null> => {
      const resp = await fetch(`/api/v1/instruments/${encodeURIComponent(instrumentId ?? "")}`);
      if (!resp.ok) return null;
      const body = (await resp.json()) as { instrument: InstrumentNameProfile };
      return body.instrument;
    },
  });
  return data ?? null;
}
