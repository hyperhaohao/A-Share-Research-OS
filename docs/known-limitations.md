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

---

> 2026-08-30 增补（Guanlan Direct Port G10 验收）。

10. **K 线端点（本机网络）**：东方财富 kline 端点对本机网络断连（容器与宿主
    一致，疑 TLS 指纹拦截）→ 工作流 Data 节点/策略回测的完成路径在本机走
    诚实失败显形；确定性完成路径由后端测试覆盖。源恢复后真机自动可用。
11. **Workflow Studio 节点目录**：目录与执行器强对应（data/rule/expression/
    validation/output 五类可真实执行）；donor 的因子/ML/回测类节点待因子
    引擎接入后进目录（目录=可执行，不摆不可跑的节点）。
12. **风险偏好温度计 / 预测市场**：全球宏观页风险区显形「暂无源」；
    PM/Kalshi/VIX 类源接入前不渲染温度。
13. **盯盘 AI 研判**：决策保持确定性规则（可复现）；LLM 研判与条件单编辑
    待 ASRO_LLM_API_KEY 后评估接入。
