# PLAN.md

# A-Share Research OS — Execution Plan

> 当前执行线为整改（R0–R5），依据 `A-Share-Research-OS-整改实施任务书.md`；
> 任务清单与状态见 `REMEDIATION.md`。首轮 M0–M29 计划保留于文末历史节。

---

# Remediation Phases（当前执行）

## R0 — State & Integrity Repair（DOING）
- [x] REMEDIATION.md 建立
- [x] STATUS 重写为整改态 + 历史归档 docs/milestones/
- [ ] ROADMAP 整改阶段表
- [ ] RunManifest 真实值（git commit / SHA256 config / 真实 seed）
- [ ] Gate 绕过修复（or True / 估值假设占位）
- [ ] 测试重分类（pytest markers: api_integration / live）
- [ ] Build + 全量测试 + checkpoint

## R1 — Real Research Data（TODO）
- [ ] 行情 fallback provider
- [ ] Announcements（巨潮）/ Financials（三大报表）/ News / Capital Flow / Industry / Macro
- [ ] Live 验证 3-5 只 × 4 能力 → Evidence + Manifest

## R2 — Full Research Pipeline（TODO）
- [ ] Analyst 集（Financial/Event/News/Industry/Macro/CapitalFlow/Risk）
- [ ] ClaimCompiler / ThesisBuilder（强制引用）
- [ ] Debate 入主链 + ScenarioEngine + ValuationInputBuilder（证据输入）+ RiskManager
- [ ] Live：一只真实股票全链（无手工补链）

## R3 — AI / Quant / Continuous（TODO）
- [ ] LLMProvider（OpenAI-compatible）+ 边界落地 + Copilot + 双语 Narrative Layer
- [ ] TideQuantAdapter → QuantBrief 进 Research State
- [ ] 后台 scheduler 服务 + Monitor→Materiality→Delta/Full 接主链

## R4 — Research Workspace（TODO）
- [ ] Stock Workspace 九 Tab + Copilot + Thesis/Financial/Valuation UI + React Flow Graph
- [ ] Interactive Report 补全（Counter Evidence/Revalue/Diff/Accept/Reject/History）

## R5 — Production Research E2E（TODO）
- [ ] 4-6 只真实 A 股 Live Research E2E 全链
- [ ] 长时运行测试 + 生产复验（compose/backup/restore）+ Final Reviewer

---

# 首轮交付历史（M0–M29 计划）

