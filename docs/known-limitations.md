# Known Limitations（任务书 §98「known limitations」）

> 2026-08-28。按影响排序；均不阻断研究闭环交付。

1. **交易日历近似**：预测 due 按周末跳过计算，未接入法定节假日日历。
   影响预测到期日（±1-3 天）；来源接入后在 M3 calendar 扩展。
2. **基准指数序列**：验证的超额收益需基准（如沪深300）指数行情证据；
   IDX 数据源未接入前 `excess_return` 显式为 null（不猜测）。
3. **PDF 导出**：已实现（reportlab + 内置 Adobe CJK 字体 STSong-Light，浅色 A4）；
   如需与屏幕 HTML 完全同像素的排版，可另接无头 Chromium 打印。
4. **认证**：首版单用户/内网定位，API 无登录体系；公网部署必须加 auth + TLS（security.md）。
5. **LLM 分析师**：M8 起分析师为确定性规则（可验证、可复现）；LLM 驱动的自由分析
   接入时复用同一 AnalystBrief 契约与引用完整性校验。
6. **指标数据**：估值引擎输入（EPS/BVPS 等）来自财报证据；财报 provider 接入前
   涉及财报的估值方法返回显式 not-computable。
7. **假日历/港股/美股**：当前仅 A 股（沪深北）；架构已按市场参数化。
8. **数据库规模**：当前默认 SQLite 仅适合单用户/内网/低并发试用规模；
   多用户长期 scheduler 需迁移 PostgreSQL（docker-compose.production.yml 后续提供）。
9. **Macro 官方源**：宏观/政策当前为 Eastmoney 搜索 + 机构标注（media_report B2）；
   gov.cn 等官方原始源（B1/A1）待接入。
