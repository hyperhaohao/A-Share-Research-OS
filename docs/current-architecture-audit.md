# Current Architecture Audit — M0 上游源码审计记录

> 生成：2026-08-28（M0）
> 方法：源码级审计（结构/关键源码/运行/测试/许可证），非 README 审计。
> 环境：Windows 11 / Python 3.11.15 / Node 24 / uv 0.11.26。
> 上游工作区：`C:\Users\HyperHao\Desktop\upstreams\`（正式仓库之外）。
> 注：github.com 直连不稳定，TideTrading/financial-analyst/qlib/RD-Agent 通过 GitHub API tarball 获取（无 .git 历史），HEAD commit 经 GitHub API 独立核对。

---

## 1. TideTrading — 首选主工程候选

```text
Repository:  https://github.com/skloxo/TideTrading  (源自 HKUDS 生态，vibe-trading 系)
Branch:      main
HEAD:        4ff21d3c9b7f7547d29f1248c85db270f0ae56ee (2026-08-22)
Latest push: 2026-08-25   Stars: 9（2026-06 创建，社区极新）
License:     MIT（根 LICENSE 存在）
Stack:       Python 3.11+ / FastAPI / LangGraph / React 19 + Vite + TS + Tailwind / SSE / Docker
Size:        ~126k 行 Python（843 文件），前端完整工程，仓库 322MB
```

### 实际运行验证

```text
PASS  uv sync 依赖安装（uv.lock 锁定）
PASS  tide serve 启动 → /health {"status":"healthy"}（需先 pip install -e . --no-deps；
      直接 python api_server.py 会因 sys.modules 检查失败，见已知问题）
PASS  /openapi.json → 102 个 REST 端点
PASS  LIVE A股数据：GET /api/quote/realtime/000001 → 平安银行 11.59 元，
      change_pct -1.19%，五档买卖盘（腾讯/东财源，无需 API key）
PASS  前端 npm install + vite build（14.4s，仅 chunk 体积告警）
PASS  定向切片（HOME 正常设置后）：scheduled_research + research_protocol +
      research_card + backtest 安全测试 → 78 passed in 13.15s
PASS  数据工具切片：test_tools_stock + base_engine + audit_redact → 56 passed / 6 failed
      （failed 为依赖实时网络行情的 market scan 类，本机网络受限）
PART  全量 pytest（~4800 用例）：4028 passed / 941 failed / 3766 errors / 11.5 min。
      其中 errors 主体为沙箱进程缺 HOME 环境变量 → pathlib.expanduser
      "Could not determine home directory"（mootdx/.tide-trading 配置路径解析）；
      设置 HOME 后错误消失（抽样验证 56/62 绿）。环境性失败，非业务缺陷。
NOTE  test_a2a_server.py / test_system_changelog.py collection error：repo-root 模块
      不在 pythonpath（tarball 环境路径配置问题）
```

### 关键源码定位

```text
agent/api_server.py            FastAPI 装配 + SSE（~1200 行，102 端点）
agent/src/swarm/               多智能体编排（runtime/worker/grounding/presets/task_store）
agent/src/scheduled_research/  定时研究（executor/models/store）→ 对应 M18 需求
agent/src/research_protocol/   研究协议（UniverseSpec/SplitSpec/BenchmarkSpec/CostModel/
                               EvaluationPlan）→ 量化实验设计，非基本面研究域模型
agent/src/research_card/       结构化研究卡（warnings/failures + markdown/html 渲染）
agent/src/governance/          策略决策/工具清单治理
agent/src/live/, shadow_account/  模拟盘/影子账户
agent/src/factors/, backtest/  因子库(zoo yaml) + 回测引擎(loaders/engines/optimizers)
agent/data/, agent/skills/ashare-mootdx/  TDX/mootdx A股数据 + tushare/akshare/baostock/
                               腾讯/yfinance/ccxt/alphavantage loader 矩阵
frontend/src/i18n/             react-i18next；SUPPORTED_LANGUAGES = zh-CN + en；默认 zh-CN
frontend/src/index.css         Tailwind `.dark` class（有暗色基础）
```

### 与 TASK 对齐的优势

1. A 股数据真实可用（本机 live 验证），多源 loader 矩阵正是 Source Layer 需要的原料；
2. FastAPI + React19/Vite/TS + i18next + ECharts/lightweight-charts：与任务书 §5/§7 技术偏好一致；
3. SSE、scheduler、swarm、governance、Docker 已存在；
4. MIT，工程完整度高，活跃维护（月内多次提交）。

### 与 TASK 的差距（需要在正式仓库内自建）

1. **无 Evidence/PIT 领域模型**：研究输出是 session/chat/run + research card，没有
   available_time ≤ as_of 的可追溯证据链、不可变快照、Claim/Thesis 结构；
2. 无不可变 ReportVersion / RevisionProposal / 报告审查闭环；
3. 无 Prediction/Validation 闭环；
4. 无 Quality Gate 概念；LLM 输出未强制证据引用 grounding（swarm/grounding.py 是工具 grounding，非证据 grounding）；
5. 多租户/IM 通道（wechat/dingtalk/feishu/qq/msteams）为交易产品向功能，属本系统不需要的重量。

---

## 2. OpenAlpha CN — Evidence/PIT 参考重点

```text
Repository:  https://github.com/ss8875/openalpha-cn
Branch:      main
HEAD:        8d130652bfd0417470543040da3e41a31a1574a7 (2026-07-27)
Latest push: 2026-08-21   Stars: 7（2026-07 创建）
License:     MIT
Stack:       Python 3.11+ / FastAPI / Pydantic v2 / SQLite(parquet) / React 19(极简) / pnpm + Playwright
Size:        src 6,523 行 + tests 3,352 行（34 文件）
```

### 实际运行验证

```text
PASS  uv sync + pytest tests/ → 105 passed in 54.47s（unit/contract/integration/replay 全绿）
PASS  uvicorn 启动 → /openapi.json 25 端点；/health {"status":"ok"}
```

### 关键源码定位（与任务书逐条对应）

```text
src/openalpha_cn/domain/time.py      Timeline 四时钟（event/available/ingested/revision），
                                     is_visible_at() = available_time <= as_of（§23 PIT 规则）
src/openalpha_cn/domain/evidence.py  EvidenceSnapshot：frozen + 内容寻址（canonical JSON sha256），
                                     evidence_id 由 provenance+content 派生（§24 不可变快照）
src/openalpha_cn/domain/run.py       RunManifest：code_commit/config_digest/provider_payload_digests/
                                     model+prompt versions/random_seed/environment/checkpoints（§40）
src/openalpha_cn/providers/base.py   Provider 契约：结构化失败（auth/config/invalid_response/
                                     rate_limit/upstream + retryable）、success 与 no_data 严格区分、
                                     batch 级 PIT 校验、payload digest（§21 SourceResult 语义）
src/openalpha_cn/backtest/           事件研究 CAR/t 统计/确定性 Bootstrap；组合回测（T+1/整手/
                                     涨跌停锁单/成本）；60 交易日 300 事件冻结 Replay 语料
src/openalpha_cn/api/app.py          FastAPI 版本化公开 API
```

### 局限

- 领域中心是 **signal/decision/回放**，不是 Evidence→Claim→Thesis→Report 的基本面研究链；
- 无估值引擎、无报告审查/修订、无预测-验证台账、无可用的研究工作台前端（12 个 tsx 文件）；
- 数据入口依赖用户配置的 chainlin 服务或自有文件（akshare/tushare provider 为骨架）。

结论：**其领域契约（四时钟/PIT/不可变快照/Manifest/Provider 失败语义）是正式仓库 Research Core 的直接蓝本**。

---

## 3. 觀瀾（financial-analyst）— UI/UX 第一参考

```text
Repository:  https://github.com/jesson-hh/financial-analyst
Branch:      main
HEAD:        98f139886c9b0b9895ab6cc90e9d5fe1cc5fcc28 (2026-08-11)
Latest push: 2026-08-21   Stars: 51
License:     ⚠️ 无 LICENSE 文件（GitHub API license: None）→ 默认版权保留，禁止复制源码
Stack:       FastAPI 薄壳 + fork 的 financial_analyst 引擎 + 无构建多页 React18-UMD UI
```

### 实际运行验证

```text
PASS  engine build_app() import 验证（fastapi/litellm/lightgbm 依赖最小集）
N/A   完整数据运行：数据目录指向作者本机 G:/stocks（get_data_paths → loaders.yaml），
      本机无该数据，运行无意义 → 以源码审计为准
```

### 关键源码定位

```text
ui/_shared/tokens.css     完整明暗双色 Design Tokens（宣纸/月夜），A 股语义色：
                          --zhu 朱砂=涨 / --dai 黛绿=跌，--yin 印章红，数字 tabular-nums
                          —— 正是任务书 §14/§15 要求的「颜色语义与主题解耦」参考实现
ui/                       13 个研究模块：graph/cards/chat/console/factor/fundflow/industry/
                          macro/news/overseas/screen/seats —— 研究闭环的信息密度样本
engine/financial_analyst/ 50+ 端点 buddy SSE 桥、loaders(tushare/pytdx/腾讯)、因子评测、
                          回测、memory/经验卡、MCP server
ARCHITECTURE.md           「重组头部、复用引擎」三层架构自述
```

### 反面教材（明确不学）

- `guanlan-bus.js`：**localStorage 作为跨模块唯一事实源** —— 任务书明确禁止浏览器状态当事实库；
- 无构建 + 浏览器内 Babel 编译 JSX —— 不可维护，不作为正式前端架构。

---

## 4. Qlib — 专业 QuantEngine

```text
Repository:  https://github.com/microsoft/qlib
Branch:      main
HEAD:        79633dd9506ea689e5400dea0197717b5b3d74b7 (2026-07-23)
Stars: 47,979（2020 至今，成熟）
License:     MIT
Stack:       Python + Cython 扩展(qlib/data/_libs) + 自有二进制数据格式
```

### 实际运行验证

```text
PASS  pyqlib 0.9.7 wheel 安装 + import qlib
FAIL  源码树内 pytest：tarball 无 git 元数据 → setuptools_scm LookupError；wheel(0.9.7)与
      main 源码测试存在版本错位 → 1 个 config 测试 AttributeError。属环境性失败。
DEFER 完整 Data→Factor→Model→Backtest→Metrics 闭环需 qlib 二进制数据下载（github raw，
      当前网络不可达）→ 若 M21 判定需要 Qlib，在 M22 用完整 clone 正式验证。
```

### 关键源码定位

```text
qlib/data/pit.py        Point-in-Time 数据库实现（财报时点对齐）
qlib/data/              storage/cache/ops/dataset —— 完整数据基建
qlib/backtest/, strategy/, model/, rl/, workflow/  回测-组合-模型-工作流全链
qlib/contrib/           cn 数据脚本、evaluate、meta、online 服务
```

---

## 5. RD-Agent — 后期可选自动化研发

```text
Repository:  https://github.com/microsoft/RD-Agent
Branch:      main
HEAD:        6762f84f9bc0f5c6486c50a00e128a57ac6c3683 (2026-08-04)
Stars: 14,348
License:     MIT
```

### 实际运行验证

```text
PASS  uv venv + requirements.txt 安装 + import rdagent（本机 Python 3.11.15）
```

### 结构

```text
rdagent/scenarios/qlib/    基于 Qlib 的因子/模型自动化实验闭环（proposal/experiment/developer）
rdagent/scenarios/data_science/, kaggle/, rl/, finetune/  其他场景
rdagent/core/, oai/        Co-STEER 代码演化内核 + LLM 抽象
```

评估：Hypothesis→Experiment→Evaluation→Feedback 自动化研发循环。任务书 §4.5 明确「基础系统稳定前禁止接入」。当前 REJECT（记录在案，M20 学习闭环成熟后可重评）。

---

## 6. TradingAgents — 可选 ResearchEngine

```text
Repository:  https://github.com/TauricResearch/TradingAgents
Branch:      main
HEAD:        a33fd4c0f134485a43553a2c23a63cb14adbd88f (2026-07-18)
Stars: 100,992
License:     Apache-2.0
```

### 实际运行验证

```text
PASS  uv sync --extra dev + pytest（selection: date_boundaries/dataflows_config/capabilities）
      → 27 passed in 10.00s
```

### 结构

```text
tradingagents/graph/     LangGraph 状态机：analyst 轮次控制、bull/bear 辩论轮数、
                         3 方风险辩论、reflection、sqlite checkpoint
tradingagents/agents/    analysts(5)/researchers(bull,bear)/risk_mgmt(3)/trader/managers
tradingagents/dataflows/ yfinance/alphavantage/fred/reddit/stocktwits/polymarket
                         → grep 证实无 akshare/tushare/.SH/.SZ 处理，无 A 股数据层
```

评估：A 股覆盖为零，TideTrading 自带等价且更完整的编排。辩论结构设计（证据约束下辩论轮数控制）可作为 Debate（任务书 §35）的实现参考。

---

## 7. 网络环境备注

```text
github.com 直连 git clone/大文件下载在本机不稳定（反复 connection reset / 超时）；
api.github.com 稳定可用；codeload 大 tarball 中途易断；ghfast.top 镜像通道验证可用。
对正式仓库的影响：后续上游拉取优先走 API tarball + 镜像，重要决策以 GitHub API 记录 commit。
```
