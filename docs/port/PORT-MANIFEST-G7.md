# PORT-MANIFEST — G7 策略盯盘

> 依据方案 §28 建立。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/seats/luozi-app.jsx（864 行：席位盯盘主界面）
                   ui/seats/luozi-chart.jsx（372 行：SVG K线+信号标记）
                   ui/seats/luozi-panels.jsx（1673 行：研判/条件单/决策面板）
                   ui/seats/luozi-data.jsx（1839 行：数据桥）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28
ASRO target:       backend  app/api/market_data.py GET /market-data/daily-bars
                   （证据层真实日线，PIT 可见；无数据 → has_data=false 显形）
                   frontend features/strategy-monitor/：
                   MonitorCandles.tsx（K线区：G0 Candles 复用 + 信号日期
                   对位标记条）/ MonitorReplay.tsx（观察→信号→决策 合并
                   时序回放滑块）/ strategy-monitor.css；
                   StrategyMonitorDetailPage 就地装配（K线区置顶 + 回放）
ported behaviors:  K线区（donor SVG K线 → G0 Candles 组件复用）；信号在 K 线
                   时间轴对位标记（donor 信号标记习语）；决策时间线（三分离
                   记录 §24 保留）；Replay（donor 复盘回放习语 → 三分离记录
                   合并时序滑块回放——回放的是真实落库记录，非伪造事件流）；
                   条件区（monitor 策略条件经既有面板呈现）
replaced APIs:     donor luozi-data 假数据桥/window GL → ASRO strategy-monitors
                   API（Observation/Signal/Decision 三分离 §24）+
                   /market-data/daily-bars（真实证据日线）
removed mock:      donor 假行情/假研判/假决策不迁；K 线无数据 → 「暂无 K 线
                   数据 —— 日线源恢复采集后在此显示（不画假图）」（§25）
removed persistence: donor localStorage 残留 → ASRO 全服务端
remaining drift:   1. donor AI 研判 prompt 注入/条件单编辑：ASRO 决策为
                      确定性规则（§25 仅 Research Decision），LLM 研判待
                      ASRO_LLM_API_KEY 接入后评估
                   2. donor 实时价闪烁/盘口 v1 不迁（盯盘为 EOD 证据口径）
                   3. 信号标记对位需信号日落在 K 线范围内（跨范围信号仅列
                      于信号区不上图）
E2E contracts:     monitors-page/-kpi/-row/monitor-detail/-actions/monitor-run/
                   monitor-observations/-signals/-decisions/replay-feedback
                   全保留；E2E-13（诚实双路径）/E2E-16（复盘回灌）PASS
tests:             backend 367 passed（+daily-bars 端点，全量 exit 0）；
                   frontend vitest 30/30（+3：回放排序/滑块/诚实空态 + K线
                   不造假图）+ build PASS；Playwright 30/30
next (G8):         donor ui/macro/macro-app.jsx + macro-data.jsx +
                   ui/overseas/overseas-app.jsx → GlobalMacroWorkspace
                   （与全球产业坐标分离，方案 §12/§13/§39）
```
