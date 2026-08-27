# Theming（任务书 §12-§16/§77）

## 三态主题

- preference：system / light / dark，默认 system；
- `resolveTheme(preference, systemPrefersDark)` 纯函数；
- 应用：`<html data-theme="light|dark">`；
- 跟随 OS：preference=system 时监听 `matchMedia('(prefers-color-scheme: dark)')`
  change 事件实时切换；手动 light/dark 不被系统变化覆盖（§77 两语义均有测试，
  浏览器实测通过）。

## Design Tokens（§14）

`frontend/src/styles/tokens.css`：`:root[data-theme="light"]` 与
`[data-theme="dark"]` 各自定义全套变量：

```text
--color-bg / --color-bg-elevated / --color-surface / --color-border
--color-text / --color-text-secondary
--color-positive / --color-negative / --color-danger / --color-warning
--color-info / --color-accent / --shadow
```

组件只允许引用 token（代码审查项）；danger 独立于涨跌语义色。

## A 股涨跌语义（§15）

- 默认 CN 惯例：红涨（--color-positive=#c23a2f 系）绿跌（--color-negative=#2e7d54 系）；
- 暗色主题下同语义提亮（positive #e0705f / negative #5ba47e）；
- 国际惯例切换：`<html data-updown="intl">` 翻转正负色值（配色与语义解耦）；
- 红色不同时承担错误/危险 —— 错误用 --color-danger。

## 图表

ECharts/lightweight-charts 接入时读取 Theme Context 重新 applyOptions
（axis/grid/tooltip/legend 色全部来自 token）——图表基座随 M24+ 图表页启用。
