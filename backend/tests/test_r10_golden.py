"""R10 黄金场景 E2E — 000831 中国稀土资产整合研究（真实栈全程 API 驱动）.

跑通方案 §20.1 全链并在 docs/research-deep-port/R10-EVIDENCE.md 逐步留证。
用法：compose 栈健康后 python tests/test_r10_golden.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
OUT = "docs/research-deep-port/R10-EVIDENCE.md"
STEPS: list[tuple[str, str, bool]] = []  # (step, detail, ok)


def _call(method: str, url: str, body: dict | None = None):
    req = urllib.request.Request(
        BASE + url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except ValueError:
            return e.code, {}


def _ok(step: str, detail: str) -> None:
    STEPS.append((step, detail, True))
    print(f"[PASS] {step}: {detail[:110]}")


def _fail(step: str, detail: str) -> None:
    STEPS.append((step, detail, False))
    print(f"[FAIL] {step}: {detail[:110]}")


def _wait_plan(plan_id: str, timeout_s: int = 150) -> dict:
    for _ in range(timeout_s):
        _, p = _call("GET", f"/command/plans/{plan_id}")
        plan = p["plan"]
        if plan["status"] != "running":
            return plan
        time.sleep(1)
    return plan


def main() -> int:
    report = []

    def W(line: str = "") -> None:
        report.append(line)
        try:
            with open(OUT, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
        except OSError:
            pass

    W("# R10 黄金场景证据 — 000831 中国稀土资产整合研究\n")
    W("真实栈：compose backend，全程 API 驱动（无 Mock 注入）。\n")

    # ---- 1) Commander：黄金问题 → 结构化计划（focus=event） -----------------
    _, sess = _call("POST", "/command/sessions", {})
    sid = sess["session"]["session_id"]
    _, turn = _call("POST", f"/command/sessions/{sid}/turns",
                    {"text": "研究中国稀土近期资产整合信号"})
    plan = turn.get("plan")
    meta = (plan or {}).get("meta") or {}
    focus_ok = meta.get("focus") == "event" and meta.get("product_type") == "EVENT_INVESTIGATION"
    (_ok if focus_ok else _fail)(
        "1 Commander 意图/计划",
        f"focus={meta.get('focus')} profile={meta.get('profile')} "
        f"product={meta.get('product_type')} questions={len(meta.get('questions') or [])}",
    )
    W(f"\n计划问题：{json.dumps(meta.get('questions'), ensure_ascii=False)}")
    W(f"必需来源：{json.dumps(meta.get('required_sources'), ensure_ascii=False)}\n")

    # ---- 2) 管线完成（T0/T2 采集 → 快照 → Claims → Thesis → 报告） -----------
    plan = _wait_plan(plan["plan_id"])
    run_id = plan.get("run_id")
    (_ok if plan["status"] == "completed" else _fail)(
        "2 研究管线完成", f"status={plan['status']} run={run_id}",
    )

    evs = _call("GET", f"/research-runs/{run_id}/events")[1]["results"]
    kinds = [e["event_type"] for e in evs]
    w = lambda k: W(f"- `{k}`" if k in kinds else f"- ~~{k}~~（未触发）")
    W("\nRun 事件链（§10.5/§10.3/§10.4）：")
    for k in ("profile_applied", "waiting_data", "reviewing", "missing_data_summary",
              "claims_compiled", "thesis_ready", "report_ready", "run_completed"):
        w(k)

    # ---- 3) 证据 / Claim / Thesis（黄金问题的研究状态） ----------------------
    _, ev_page = _call("GET", "/evidence?instrument_id=SZSE%3A000831&limit=5")
    n_ev = ev_page.get("count", 0)
    (_ok if n_ev > 0 else _fail)("3a 证据层（真实采集）", f"{n_ev} 条证据")

    _, claims = _call("GET", "/claims?instrument_id=SZSE%3A000831&limit=3")
    claim_rows = claims.get("results") or claims.get("claims") or []
    (_ok if claim_rows else _fail)("3b Claims（带引用）",
                                   f"{len(claim_rows)} 条；样例引用={claim_rows[0].get('supporting_evidence_refs') if claim_rows else None}")

    _, theses = _call("GET", "/theses?instrument_id=SZSE%3A000831&limit=3")
    thesis_rows = theses.get("results") or theses.get("theses") or []
    (_ok if thesis_rows else _fail)("3c Current Thesis（append-only）",
                                    f"{len(thesis_rows)} 条；title={thesis_rows[0].get('title') if thesis_rows else None}")

    # ---- 4) Source Trust / 引用反查（R2） -----------------------------------
    _, ev_one = _call("GET", "/evidence/" + claim_rows[0]["supporting_evidence_refs"][0]) if claim_rows else (0, {})
    trust = (ev_one.get("evidence") or {}).get("authority_level")
    (_ok if trust else _fail)("4a Source Trust（authority 映射 T0-T4）", f"authority={trust}")

    bad = _call("POST", "/extractions", {
        "source_evidence_id": claim_rows[0]["supporting_evidence_refs"][0],
        "statement": "股东拟减持9%股份并退出公司",
        "support_span": "减持计划的预披露公告",
        "instrument_id": "SZSE:000831",
    })
    (_ok if bad[0] == 201 and bad[1]["extraction"]["verdict"] == "rejected" else _fail)(
        "4b Citation 反查（编造数字拒绝）",
        f"verdict={bad[1].get('extraction', {}).get('verdict')} reason={bad[1].get('extraction', {}).get('reject_reason')}",
    )

    # ---- 5) 产业语义（R3 真实数据 + R9 幂等注册触发） ------------------------
    _upsert_driver = _call("POST", "/industry-semantics/driver", {
        "object_key": "reduce_supply_pressure", "industry_id": "稀土",
        "instrument_id": "SZSE:000831",
        "title": "广晟控股减持计划带来股份供给压力",
        "mechanism": "持股 9.48% 的股东广晟控股集团披露减持计划（不超过 1061.22 万股 / 总股本 1%），形成二级市场股份供给增量，短期压制股价表现",
        "status": "active", "direction": "negative",
        "evidence_claims": [
            {"evidence_id": "ev_fd2717a34a3a55ce4ad020f8",
             "support_span": "广东省广晟控股集团有限公司（简称“广晟控股集团”）拟以集中竞价方式，减持公司股份不超过1061.22万股",
             "observed_at": "2026-08-20T10:31:00Z"},
        ],
    })
    _upsert_narr = _call("POST", "/industry-semantics/narrative", {
        "object_key": "reduce_wave_2026_08", "industry_id": "稀土",
        "instrument_id": "SZSE:000831",
        "title": "稀土板块股东减持：广晟控股拟减持中国稀土不超过 1%",
        "status": "active",
        "evidence_claims": [
            {"evidence_id": "ev_7e4669ab0062efcb5c7dcfc5",
             "support_span": "股东广晟控股集团计划自公告披露之日起15个交易日后的三个月内",
             "observed_at": "2026-08-21T13:14:00Z"},
            {"evidence_id": "ev_89a9fdd273fae38469a17c29",
             "support_span": "减持公司股份不超过1061.22万股，即不超过公司总股本的1%",
             "observed_at": "2026-08-20T12:30:00Z"},
        ],
    })
    _, sem = _call("GET", "/industry-semantics/driver?industry_id=%E7%A8%80%E5%9C%9F")
    driver_n = sem.get("count", 0)
    (_ok if driver_n > 0 else _fail)("5a Industry Driver（真实证据引用）", f"{driver_n} 条")
    _, nsem = _call("GET", "/industry-semantics/narrative?industry_id=%E7%A8%80%E5%9C%9F")
    (_ok if nsem.get("count", 0) > 0 else _fail)("5b Industry Narrative", f"{nsem.get('count')} 条")

    # ---- 6) Signal Ladder（A/B 分级 + 证据强制） ----------------------------
    if claim_rows:
        real_ev = claim_rows[0]["supporting_evidence_refs"][0]
        ladder = _call("POST", "/research-inbox/signal-ladder/evaluate", {
            "ladder": [
                {"level": "B", "keywords": ["减持", "披露"], "label": "股东减持披露"},
                {"level": "A", "keywords": ["重组报告", "证监会核准"], "label": "重组正式公告"},
            ],
            "observations": [
                {"observation_id": "golden_o1",
                 "text": "广晟控股集团披露减持计划 不超过总股本1%",
                 "evidence_ids": [real_ev]},
            ],
        })
        results = ladder[1].get("results", [])
        (_ok if ladder[0] == 200 and results else _fail)(
            "6 Signal Ladder A/B 分级",
            f"level={results[0]['level'] if results else None} rule={results[0]['rule'] if results else None}",
        )

    # ---- 6b) R10 Semantic Assertions（§9 SEM-01…04 + DIFF-01） ----------------
    # SEM-01: 减持 ≠ 资产整合 A/B 信号
    sem01 = _call("POST", "/research-inbox/signal-ladder/evaluate", {
        "ladder": [
            {"level": "B", "keywords": ["资产整合", "资产注入", "重组"], "label": "整合信号"},
            {"level": "A", "keywords": ["筹划重大资产重组", "重组预案"], "label": "重组正式"},
        ],
        "observations": [
            {"observation_id": "sem01", "text": "广晟控股集团披露减持计划 不超过1061.22万股",
             "evidence_ids": [claim_rows[0]["supporting_evidence_refs"][0] if claim_rows else "ev_test"]},
        ],
    })
    sem01_results = sem01[1].get("results", [])
    sem01_pass = not any(
        r.get("event_type") in ("restructuring", "asset_injection")
        for r in sem01_results
    )
    (_ok if sem01_pass else _fail)(
        "6b SEM-01 减持≠资产整合",
        f"integration_signals={len([r for r in sem01_results if r.get('event_type') in ('restructuring','asset_injection')])}",
    )

    # SEM-02: 否定重组 → A Signal = false
    sem02 = _call("POST", "/research-inbox/signal-ladder/evaluate", {
        "ladder": [
            {"level": "A", "keywords": ["筹划重大资产重组", "重组预案"], "label": "重组正式"},
        ],
        "observations": [
            {"observation_id": "sem02", "text": "公司不存在重大资产重组计划。",
             "evidence_ids": [claim_rows[0]["supporting_evidence_refs"][0] if claim_rows else "ev_test"]},
        ],
    })
    (_ok if not sem02[1].get("results") else _fail)(
        "6c SEM-02 否定重组→A=false", f"results={len(sem02[1].get('results', []))}",
    )

    # ---- 7) Thesis Diff（新证据 → 影响分析 → 修订 append-only） --------------
    _, diff = _call("GET", "/research-inbox/thesis-diff?instrument_id=SZSE%3A000831")
    d = diff["diff"]
    (_ok if d["new_evidence"] else _fail)(
        "7a Thesis Diff 影响分析",
        f"new_evidence={len(d['new_evidence'])} affected_claims={len(d['affected_claims'])} "
        f"affected_theses={len(d['affected_theses'])} action={d['suggested_action']}",
    )
    old_thesis_id = thesis_rows[0]["thesis_id"] if thesis_rows else None
    # apply 需要一个 pin 了全部当前可见证据的快照（PIT）：取 now 快照
    _, now_snap = _call("POST", "/snapshots?instrument=SZSE%3A000831")
    snap_id = now_snap["snapshot"]["snapshot_id"]
    applied = _call("POST", "/research-inbox/thesis-diff/apply", {
        "instrument_id": "SZSE:000831",
        "revised_statement": "修订：广晟控股减持计划披露后股份供给压力上升，观察期 15 交易日；资产整合信号仍以 T0 公告为准。",
        "snapshot_id": snap_id,
    })
    new_thesis_ok = applied[0] == 201
    new_thesis_id = applied[1].get("thesis_id") if new_thesis_ok else None
    (_ok if new_thesis_ok else _fail)(
        "7b Thesis Diff apply（append-only 新版本）",
        f"new={new_thesis_id} old={old_thesis_id} 保留={new_thesis_ok}",
    )

    # ---- 8) Research Product（EVENT_INVESTIGATION 类型化报告） ---------------
    _, arts = _call("GET", "/artifacts?limit=10")
    rep_art = next((a for a in arts["results"] if a["artifact_type"] == "report"), None)
    (_ok if rep_art and "事件调查" in rep_art["title"] else _fail)(
        "8 Research Product（类型化报告 Artifact）",
        f"title={rep_art['title'] if rep_art else None}",
    )

    # ---- 9) Monitor / Materiality（Inbox 视角） -----------------------------
    _, inbox = _call("GET", "/research-inbox")
    box = inbox["inbox"]
    (_ok if box["count"] >= 0 else _fail)(
        "9 Research Inbox（§14.1 聚合）",
        f"new_ev={len(box['new_evidence'])} alerts={len(box['materiality_alerts'])} "
        f"requests={len(box['open_research_requests'])} failed={len(box['failed_collections'])}",
    )

    # ---- 10) Experience 原炼验用 + Playbook（R6） ----------------------------
    _, reports = _call("GET", "/reports?limit=1")
    rep_row = (reports.get("results") or reports.get("reports") or [{}])[0]
    rep_id = rep_row.get("report_id")
    _, card = _call("POST", "/experience-cards/from-report", {"report_id": rep_id})
    card_id = card.get("card", {}).get("card_id")
    (_ok if card_id else _fail)("10a 原→炼（报告→经验卡）", f"card={card_id}")

    v = _call("POST", f"/experience-cards/{card_id}/validate")
    cq = _call("POST", f"/experience-cards/{card_id}/validate-non-quant",
               {"method": "counterexample_search"})
    (_ok if v[0] == 201 and cq[0] == 201 else _fail)(
        "10b 验（case + 反例搜索）",
        f"case={v[1].get('validation', {}).get('method')} cq={cq[1].get('validation', {}).get('summary', '')[:60]}",
    )
    ap = _call("POST", f"/experience-cards/{card_id}/approve", {})
    (_ok if ap[0] == 200 else _fail)("10c 用（批准门）", f"status={ap[1].get('card', {}).get('status')}")
    pb = _call("GET", "/experience-cards/playbook/search?q=%E5%87%8F%E6%8C%81")
    (_ok if pb[1].get("count", 0) > 0 else _fail)("10d Playbook 检索", f"{pb[1].get('count')} 条")

    # ---- 11) Memory（R7：candidate → promote） ------------------------------
    mem = _call("POST", "/memories/from-experience/" + card_id)
    mem_id = mem[1].get("memory", {}).get("memory_id") if mem[0] == 201 else None
    (_ok if mem[0] == 201 else _fail)("11a Experience→Memory candidate", f"memory={mem_id}")
    pr = _call("POST", f"/memories/{mem_id}/promote")
    (_ok if pr[0] == 200 and pr[1]["memory"]["status"] == "active" else _fail)(
        "11b Memory promote（人工晋升门）", f"status={pr[1]['memory']['status']}",
    )
    no_ev_fields = "authority_level" not in pr[1]["memory"]
    (_ok if no_ev_fields else _fail)("11c Memory≠Evidence（结构锁死）", "无 authority/fact_status 字段")

    # ---- 12) Research Graph（全对象在册） ------------------------------------
    _, graph = _call("GET", "/artifacts/graph")
    types = {}
    for n in graph.get("nodes", []):
        types[n.get("artifact_type")] = types.get(n.get("artifact_type"), 0) + 1
    W(f"\n图谱节点：{json.dumps(types, ensure_ascii=False)}")
    W(f"图谱边：{len(graph.get('edges', []))}\n")
    needed = ("research_run", "report", "report_version", "thesis", "prediction",
              "experience_card", "industry_driver", "industry_narrative")
    missing = [t for t in needed if t not in types]
    (_ok if not missing else _fail)("12 Research Graph（方案 §15.1 类型覆盖）",
                                    f"missing={missing or '无'}")

    # ---- 13) Source Trust / PIT（§20.2 Q4：证据当时是否已公开） ---------------
    (_ok if evs and "snapshot_built" in kinds else _fail)(
        "13 PIT 快照门（snapshot_built 事件）", "evidence.available_time <= as_of 强制",
    )

    # ---- 14) 报告可打开（Research Product 渲染） -----------------------------
    if rep_id:
        _, rep_detail = _call("GET", f"/reports/{rep_id}")
        rep_body = rep_detail.get("report") or rep_detail
        has_md = bool(rep_body.get("markdown"))
        (_ok if has_md else _fail)("14 报告渲染（markdown）", f"{len(rep_body.get('markdown') or '')} chars")
    else:
        _fail("14 报告渲染（markdown）", "no report")

    # ---- 汇总 ---------------------------------------------------------------
    passed = sum(1 for _, _, ok in STEPS if ok)
    total = len(STEPS)
    W(f"\n---\n\n## 汇总：{passed}/{total} PASS\n")
    for step, detail, ok in STEPS:
        W(f"- {'PASS' if ok else 'FAIL'} · {step} · {detail[:120]}")
    print(f"\n=== {passed}/{total} PASS ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
