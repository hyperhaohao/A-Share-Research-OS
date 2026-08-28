# Quant Audit — M21（任务书 §54）

> 日期：2026-08-28。
> 问题：主工程（TideTrading，ADR-001 ADOPT）已有的 quant 能力是否满足本系统需求？
> 是否需要接入 Qlib（M22）？
> 证据：对 `upstreams/TideTrading/agent` 的源码级审计（M0 工作区）。

---

## 1. 主工程已有 quant 能力（源码证据）

### 1.1 因子库 `agent/src/factors/`（约 2.8 万行）

```text
zoo/alpha101   104 个文件 —— WorldQuant Alpha101 因子集
zoo/gtja191    194 个文件 —— 国泰君安191因子（A股原生因子集）
zoo/qlib158    158 个文件 —— Qlib 官方因子集的移植
zoo/academic   学术因子样本
registry.py / base.py / factor_analysis_core.py / bench_runner.py(+strict) / compare_runner.py
```

要点：**Qlib 的 158 因子集已经被移植进主工程**（qlib158），gtja191 更是 A 股专属。

### 1.2 回测引擎 `agent/backtest/`（约 1.26 万行）

```text
engines/china_a.py      ChinaAEngine —— A股专用撮合：T+1（当日买入不可卖）、
                        佣金万2.5（最低5元）、印花税万5（仅卖出）、过户费；
                        涨跌停价格约束
engines/                china_futures / crypto / forex / global_equity / composite
loaders/ optimizers/    数据加载与参数优化
metrics.py models.py validation.py run_card.py benchmark.py correlation.py
```

### 1.3 量化真实性测试

```text
tests/quant/    IC horizons、capacity（容量）、cost sensitivity（成本敏感性）、
                crowding（拥挤度）、execution realism（执行现实性）、
                hard failures、alpha/backtest scorecard integration
tests/factors/  alpha101/academic 样本回归
```

### 1.4 本系统已有的量化能力（M10/M4）

- 确定性估值引擎（PE/PB/PS/EV-EBITDA/DCF/DDM/历史分位/同业比较，固定数值单测）；
- 事件研究级统计在 OpenAlpha CN 蓝本中可用（CAR/t 统计/Bootstrap，MIT 可移植）。

---

## 2. 需求对比（任务书 §54/§97）

| 需求 | 主工程能力 | 结论 |
|------|-----------|------|
| alpha/factor | alpha101+gtja191+qlib158（450+ 因子）+ 注册/IC 分析 | 满足 |
| backtest | ChinaAEngine（T+1/费率/涨跌停）+ 多市场引擎 + 优化器 | 满足 |
| model/optimizer | 参数优化器 + ML 策略管线（scikit-learn 栈） | 满足 |
| metrics | metrics.py + scorecard + IC/容量/成本/拥挤度测试 | 满足 |
| PIT 财报时点 | Qlib `data/pit.py` 强项 —— 但本系统在 M4/M5 已自建四时钟 PIT | 已自建 |
| ML 因子挖掘全自动化 | RD-Agent/QLib 管线 —— 属研究自动化，非本 TASK 必需 | 不需要 |

## 3. 决定：M22 = NOT_REQUIRED

理由：

1. 主工程已有 **Qlib 因子集移植（qlib158）+ A股专用回测引擎（T+1/费率/涨跌停）**
   + 完整真实性测试 —— §97 要求的 `Factor/Feature → Model → Prediction → Backtest
   → Metrics` 闭环在主工程内已有真实实现；
2. Qlib 的增量价值（自有二进制数据格式 + ML 因子挖掘管线 + Cython 数据内核）与
   主工程能力重叠，且引入重依赖（Cython 构建、独立数据仓库）违反「不得为满足清单
   同时维护两套重复量化底层」（§12）；
3. 本系统的差异化价值在研究闭环（Evidence/PIT/报告/预测验证），量化底层复用主工程。

## 4. 重评触发条件

- 研究闭环需要 ML 因子挖掘自动化（Hypothesis→Experiment 全自动）时重评；
- ChinaAEngine 在真实数据上暴露规则缺失（如新的交易规则）且修复成本高于接 Qlib 时重评。

## 5. 与 M22 的关系

M22 不需要 Qlib Adapter 实现。若未来触发重评，按 §4.4/§54 经 Adapter 接入并完成
真实 A 股 `Data → Factor → Model → Prediction → Backtest → Metrics` 闭环后再评估。

---

## BaselineQuantEngine vs Upstream Capabilities

> 整改三轮 P1-01：明确区分正式运行时能力与上游审计能力。

### 正式运行时已接入（BaselineQuantEngine）

```text
Eastmoney kline 日线数据获取
5D 动量因子
20D 动量因子
20D 波动率因子
5D 动量信号 Long/Flat 回测（t-1 无前视）
年化收益 / Sharpe / 最大回撤 / 胜率
QuantBrief → Research State（引用 kline Evidence）
```

### TideTrading 上游已审计但未接入正式运行时

```text
Alpha101 / GTJA191 / Qlib158 因子库
450+ 因子库
ChinaAEngine（T+1 / 佣金 / 印花税 / 涨跌停）
Optimizer
完整真实性测试
```

以上 upstream 能力在 M0 审计中记录，但**不属于正式运行时已验证能力**。
如果需要高级量化，需真实接入 TideQuantAdapter 并通过集成测试。
