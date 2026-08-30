# PORT-MANIFEST — G0 Shared UI Foundation

> 依据方案 §28 建立；每迁植模块一份，随迁植进度更新。

```text
donor repo:        https://github.com/jesson-hh/financial-analyst（觀瀾）
donor path:        ui/_shared/tokens.css
                   ui/_shared/tokens-styles.css（不迁，见下）
                   ui/_shared/shared.jsx
                   ui/_shared/guanlan-nav.js（行为承接到 ASRO Router，见下）
                   ui/_shared/guanlan-bus.js（行为承接到 HandoffEnvelope，见下）
donor commit:      98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28（GitHub HEAD 2026-08-21）
ASRO target:       frontend/src/styles/guanlan-tokens.css
                   frontend/src/ui/guanlan/（组件 + guanlan.css + barrel）
ported components: Brandmark / MarketTicker / Sparkline / Candles / ResearchStep /
                   MetricCell（donor shared.jsx 全部 6 组件，TSX 化）
                   Panel / Badge / Button / Toolbar(+Sep) / Drawer / Tooltip /
                   Inspector（G0 组件集，方案 §31）
replaced APIs:     无（G0 为纯 UI 层；数据接入自 G1 起）
removed mock:      donor shared.jsx 无 mock；组件契约：无数据 → null / 不渲染
                   （方案 §25 显形原则，测试锁定）
removed persistence: 无 localStorage / 无 window 全局注册
                   （donor Object.assign(window,…) 移除 → ESM barrel 导出）
remaining drift:   1. donor inline-style 习语收敛为 gl-* 类（视觉语义 1:1，声明值保留）
                   2. dark 变体从 donor body.dark 机制改为 ASRO :root[data-theme="dark"]
                   3. --zhu-soft/--dai-soft 用 color-mix 派生（donor 为固定值，
                      映射层要求随 ASRO 语义色主题联动）
                   4. Brandmark 品牌字样按方案 §3/§27 改 ASRO（非 drift，为指定替换）
not ported:        tokens-styles.css（geek/tech 皮肤，不在 ASRO 视觉规范）
                   guanlan-bus.js（window 总线基建 —— 行为→HandoffEnvelope，方案 §21）
                   guanlan-nav.js（DOM 注入导航 —— 行为→AppShell navigation.ts，
                   ASRO 侧已存在，无需迁移动作）
i18n:              guanlan.brandSeal / guanlan.drawerClose / guanlan.drawerTitle
                   （zh-CN + en-US）；组件不携带业务文案
theme:             light / dark 全 token 化；不新增任何硬编码色值
                   （--yin 印章红为品牌印记色，独立于 danger/涨跌，方案 §20 红线）
tests:             frontend/tests/guanlan-ui.test.tsx — 12 tests（无数据显形 /
                   涨跌类名 / 三态墨痕 / Drawer 交互 / 组件 smoke）
verification:      vitest 19/19 PASS；tsc -b + vite build PASS
next (G1):         donor ui/chat/app.jsx（3442 行）→ features/command-center/
```
