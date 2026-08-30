# THIRD_PARTY_NOTICES.md

> 依据《A-Share-Research-OS-Guanlan-Direct-Port-最终迁植与集成方案》§29 建立。
> 本文件记录全部第三方来源代码的来源、许可证状态与迁植范围，随迁植进度持续更新。

---

## 1. 觀瀾 · Financial Analyst（Guanlan Direct Port donor）

| 项 | 值 |
|---|---|
| Source repository | https://github.com/jesson-hh/financial-analyst |
| Source commit（GitHub HEAD，2026-08-21 push） | `98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28` |
| 本地审计副本 | `upstreams/financial-analyst`（正式仓库之外，非 git clone） |
| 原始文件 | `ui/_shared/shared.jsx`（Brandmark / MarketTicker / Sparkline / Candles / ResearchStep / MetricCell）、`ui/_shared/tokens.css` |
| Copyright | Copyright (c) jesson-hh / financial-analyst contributors |
| ASRO 迁植目标 | `frontend/src/styles/guanlan-tokens.css`、`frontend/src/ui/guanlan/*` |

### 许可证状态（如实记录）

- donor README 顶部 badge 标注 **Apache License 2.0**；
- 截至迁植日（2026-08-30），donor 仓库根目录**未包含 LICENSE 文件**
  （GitHub API `license: null` 与 M0 审计结论一致，docs/upstream-evaluation.md
  记录觀瀾为 REFERENCE_ONLY「无 LICENSE」）；
- 本项目基于 README 所宣示的 Apache-2.0 意图按开放许可证迁植执行（方案 §29）；
  若 donor 版权方日后发布正式 LICENSE 条款或提出异议，以该条款为准并复核全部迁植文件。

### 修改说明

- `shared.jsx` → 拆分为独立 TSX 组件（TypeScript 化、JSX 属性类型化、
  inline 样式收敛为 `guanlan.css` 类、`Object.assign(window, …)` 全局注册移除）；
- `Brandmark`：观澜「觀瀾」品牌字样替换为 ASRO 品牌文案（`app.title` i18n），
  印章字符经 `guanlan.brandSeal` 本地化（方案 §3 命名 / §27 i18n）；
- `tokens.css` → `guanlan-tokens.css`：全部变量重定义为 ASRO 语义 token 的映射
  （`--paper → var(--color-bg)` 等，方案 §20 TOKEN_MAPPING），dark 变体走
  ASRO `data-theme` 机制而非 donor `body.dark`；geek/tech 双风 tokens-styles.css 不迁；
- `up/.down` 涨跌色、`.seal`、`.paper-bg`、`hr.ink-rule`、`@keyframes pulse` 行为保留。

### 未迁植（基建不迁，方案 §21）

- `ui/_shared/guanlan-bus.js` / `guanlan-nav.js`：no-build runtime 与 window 总线；
  其**跨模块行为**（handoff / 带上下文跳转）由 ASRO 既有
  `HandoffEnvelope + ResearchContext + Router`（frontend/src/shared/handoff.ts）承接；
- `ui/_shared/tokens-styles.css`（geek/tech 皮肤）：不在 ASRO 视觉规范内。

---

## 2. 其他第三方来源

| 来源 | 许可证 | 用途 | 记录 |
|---|---|---|---|
| OpenAlpha CN providers/base.py | MIT | M3 SourceResult 契约蓝本（注释注明） | docs/adr/ADR-001-main-engine-baseline.md |
| TideTrading（qlib158 等 factor 移植） | 见 docs/quant-audit.md | M21 量化能力审计引用 | docs/quant-audit.md |
