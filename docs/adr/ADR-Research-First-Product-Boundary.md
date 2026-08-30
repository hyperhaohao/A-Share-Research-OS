# ADR — Research-First Product Boundary（研究优先产品边界）

- 状态：ACCEPTED（2026-08-30，R1）
- 依据：docs/A-Share-Research-OS-观澜研究能力深迁植执行方案.md §1/§3/§7
- 关联：ADR-001（主引擎基线）、M21/M22（量化审计）、G0–G10（Experience Port，DONE）

## 背景

G0–G10 完成了观澜 Experience Layer 的产品形态迁植，但观澜真正有效的
**研究方法**（Source Trust、引用反查、产业 Driver/Transmission/Narrative、
自主研究循环、类型化研究产品、研究记忆）尚未进入 ASRO 的
Evidence/PIT/Claim/Thesis/Version/Monitor 内核——目前多为 UI 骨架 + 诚实置空。
同时 ASRO 已携带一批量化能力（因子验证工作流、筛选、策略、盯盘）。

## 决策

1. **ASRO 是面向 A 股的长期 AI Research OS**——不是选股器、不是量化框架、
   不是一次性研报生成器。系统持续维护公司/行业/事件/宏观研究状态，
   新证据出现时自动判定重要性、影响已有 Claim/Thesis、生成 Revision，
   并保留完整证据与版本历史。
2. **研究核心（Research Core）优先呈现**：一级导航以研究域为主
   （中枢/公司/产业/宏观/报告/经验/图谱/持续研究）；量化面收敛到
   「实验」分组（筛选/Workflow/Strategy/Monitor/预测）。
3. **Quant 保留但冻结**：现有量化代码与测试全部保留（不删、不断链）；
   本轮 NO NEW DEVELOPMENT——不为观澜复刻投入 Factor/IC/ML/回测，
   也不占 P0/P1 工程资源。导航/文案降为 Experimental 语义。
4. **观澜仅是 donor**：License Gate 未通过（无 LICENSE 文件）→ 全程
   REFERENCE_ONLY / BEHAVIORAL ADAPTATION；禁止大段复制 donor 源码；
   只迁概念、结构、行为与 schema 形态。
5. **单一 Research Domain**：全部新能力优先 reuse → extend → typed child →
   最后才考虑新 domain；禁止第二套 Industry/Evidence/Memory/Report 存储。
6. **不可破坏的内核红线**（Evidence First / PIT / Append-only Versioned
   State / Honest Missing Data）继续由 TASK.md 与既有质量门强制。

## 后果

- 正面：研究语义（Driver/Transmission/Narrative/Research Product/Memory）
  获得明确的工程归宿；用户第一屏看到的是研究而非交易工具。
- 代价：量化侧 UI 从一级降级（功能不受影响）；部分导航文案变更
  （视觉基线按内容变更重生成）。
- 中性：donor 无 LICENSE 的风险由 REFERENCE_ONLY 策略控制；
  若日后 donor 发布正式 LICENSE 条款，再评估是否升级复用方式。
