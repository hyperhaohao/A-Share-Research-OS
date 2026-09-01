"""F14 — 帷幄跨模块 Golden（第三轮整改任务书 §12.3，live API 驱动）.

场景（§12.3）：一句话跨模块编排 → 事件流 → 确认门（先拒绝后批准）→
Thesis 修订 → Artifact 自动打开 Workbench → 经验卡 → 后台任务 →
恢复/隔离校验。

用法：compose 栈健康后
    cd backend && python scripts/../tests/test_f14_golden_weiwo.py
（脚本写 docs/final-remediation/F14-WEIWO-GOLDEN-EVIDENCE.md）
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
OUT = "docs/final-remediation/F14-WEIWO-GOLDEN-EVIDENCE.md"
STEPS = []


def _call(method, url, body=None):
    req = urllib.request.Request(
        BASE + url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except ValueError:
            return e.code, {}


def _print(line: str) -> None:
    try:
        print(line[:150], flush=True)
    except UnicodeEncodeError:  # Windows GBK 控制台
        print(line.encode("gbk", errors="replace").decode("gbk")[:150], flush=True)


def ok(step, detail):
    STEPS.append((step, detail, True))
    _print(f"[PASS] {step}: {str(detail)[:110]}")


def fail(step, detail):
    STEPS.append((step, detail, False))
    _print(f"[FAIL] {step}: {str(detail)[:110]}")


def main():
    # ── 1) 会话 + 一句话编排 ────────────────────────────────────────────
    _, body = _call("POST", "/command/sessions")
    sid = body["session"]["session_id"]
    turn = _call("POST", f"/command/sessions/{sid}/turns",
                 {"text": "研究中国稀土近期资产整合信号"})[1]
    plan = turn.get("plan") or {}
    plan_id = plan.get("plan_id")
    if plan_id:
        ok("G1 一句话 → 结构化计划（跨模块）", f"plan={plan_id} title={plan.get('title')}")
    else:
        fail("G1 一句话 → 结构化计划（跨模块）", f"plan={plan_id}")

    # 等待计划完成
    plan_status = "running"
    for _ in range(180):
        _, p = _call("GET", f"/command/plans/{plan_id}")
        plan_status = p["plan"]["status"]
        if plan_status != "running":
            break
        time.sleep(1)
    if plan_status == "completed":
        ok("G2 计划执行完成（用户可继续对话）", f"status={plan_status}")
    else:
        fail("G2 计划执行完成（用户可继续对话）", f"status={plan_status}")

    # ── 2) 事件流：工具链 + 产物事件（§12.3 Tool Call/Result 事件化） ────
    _, ev = _call("GET", f"/command/sessions/{sid}/events")
    events = ev["results"]
    types = [e["event_type"] for e in events]
    seqs = [e["sequence"] for e in events]
    chain_ok = ("tool_call" in types and "tool_result" in types
                and "artifact_created" in types and "run_completed" in types
                and seqs == sorted(seqs) and len(set(seqs)) == len(seqs))
    detail3 = f"{len(events)} 事件"
    if chain_ok:
        ok("G3 事件流实时 + 工具链 + sequence 单调", detail3)
    else:
        fail("G3 事件流实时 + 工具链 + sequence 单调", detail3)

    # tool_call ↔ tool_result correlation
    corr_call = {e["correlation_id"] for e in events if e["event_type"] == "tool_call"}
    corr_res = {e["correlation_id"] for e in events if e["event_type"] == "tool_result"}
    if corr_call and corr_call <= corr_res:
        ok("G4 Tool Call↔Result correlation 关联", f"{len(corr_call)} calls")
    else:
        fail("G4 Tool Call↔Result correlation 关联", f"calls={len(corr_call)}")

    # ── 3) Artifact 自动打开 Workbench（§12.3） ─────────────────────────
    _, wb = _call("GET", f"/command/sessions/{sid}/workbench")
    tabs = wb["tabs"]
    if any(t["page"] == "research-report" for t in tabs):
        ok("G5 Artifact 自动打开 Workbench（报告 Tab）", f"pages={[t['page'] for t in tabs]}")
    else:
        fail("G5 Artifact 自动打开 Workbench（报告 Tab）", f"pages={[t['page'] for t in tabs]}")

    # ── 4) 刷新恢复（Snapshot → Replay） ────────────────────────────────
    _, snap = _call("GET", f"/command/sessions/{sid}/snapshot")
    if snap.get("turns") and snap.get("plans") and snap.get("latest_sequence", 0) > 0:
        ok("G6 刷新恢复（snapshot：turns/plans/latest_sequence）",
           f"seq={snap.get('latest_sequence')} turns={len(snap.get('turns', []))}")
    else:
        fail("G6 刷新恢复（snapshot：turns/plans/latest_sequence）", "incomplete snapshot")

    # ── 5) 确认门：先拒绝（无副作用）→ 再批准执行（§12.3） ───────────────
    _, theses = _call("GET", f"/command/sessions/{sid}/snapshot")
    instrument_id = None
    for p in snap.get("plans", []):
        if p.get("instrument_id"):
            instrument_id = p["instrument_id"]
            break
    instrument_id = instrument_id or "SZSE:000831"
    _, theses_before = _call("GET", f"/research-inbox/theses?instrument_id={urllib.request.quote(instrument_id)}")
    n_before = len(theses_before.get("results") or theses_before.get("theses") or [])

    created = _call("POST", "/command/confirmations", {
        "tool_name": "submit_thesis_revision",
        "arguments": {"instrument_id": instrument_id,
                      "revised_statement": "Golden：拒绝路径校验，不应生效。"},
        "command_session_id": sid,
    })
    conf_id = created[1]["confirmation"]["confirmation_id"]
    _call("POST", f"/command/confirmations/{conf_id}/decide", {"decision": "rejected"})
    rejected_exec = _call("POST", "/command/tools/submit_thesis_revision/execute",
                          {"arguments": {"instrument_id": instrument_id,
                                         "revised_statement": "Golden：拒绝路径校验，不应生效。"},
                           "confirmation_id": conf_id})
    _, theses_after_reject = _call("GET", f"/research-inbox/theses?instrument_id={urllib.request.quote(instrument_id)}")
    n_after_reject = len(theses_after_reject.get("results") or theses_after_reject.get("theses") or [])
    if rejected_exec[0] == 422 and n_after_reject == n_before:
        ok("G7 拒绝确认 → 不切换 Current（无副作用）",
           f"exec={rejected_exec[0]} theses {n_before}->{n_after_reject}")
    else:
        fail("G7 拒绝确认 → 不切换 Current（无副作用）",
             f"exec={rejected_exec[0]} theses {n_before}->{n_after_reject}")

    # 批准路径：新证据（窗口内真实证据）驱动修订
    args = {"instrument_id": instrument_id,
            "revised_statement": "Golden：广晟减持披露后供给压力上升，整合信号以 T0 公告为准。"}
    created2 = _call("POST", "/command/confirmations",
                     {"tool_name": "submit_thesis_revision",
                      "arguments": args, "command_session_id": sid})
    conf2 = created2[1]["confirmation"]["confirmation_id"]
    _call("POST", f"/command/confirmations/{conf2}/decide", {"decision": "approved"})
    executed = _call("POST", "/command/tools/submit_thesis_revision/execute",
                     {"arguments": args, "confirmation_id": conf2,
                      "command_session_id": sid, "correlation_id": conf2})
    new_thesis = executed[1].get("result", {}).get("thesis_id")
    if executed[0] == 200 and executed[1].get("ok") and new_thesis:
        ok("G8 批准 → Thesis 修订执行（confirm consumed）", f"new_thesis={new_thesis}")
    else:
        fail("G8 批准 → Thesis 修订执行（confirm consumed）", f"exec={executed[0]}")

    # 确认门事件（审计）
    _, ev2 = _call("GET", f"/command/sessions/{sid}/events")
    types2 = [e["event_type"] for e in ev2["results"]]
    if "confirmation_requested" in types2 and "confirmation_decided" in types2:
        ok("G9 确认 requested/decided 事件入流（审计）", "")
    else:
        fail("G9 确认 requested/decided 事件入流（审计）", f"types2={types2}")

    # ── 6) 经验卡（帷幄工具，§12.3） ─────────────────────────────────────
    _, arts = _call("GET", "/artifacts?limit=10")
    rep = next((a for a in arts["results"] if a["artifact_type"] == "report"), None)
    rep_id = rep["domain_id"] if rep else None
    if rep_id:
        card_out = _call("POST", "/command/tools/create_experience_card/execute",
                         {"arguments": {"report_id": rep_id}})
        if card_out[0] == 200 and card_out[1].get("ok"):
            ok("G10 经验卡提炼（帷幄工具结构化结果）",
               f"card={card_out[1].get('result', {}).get('card_id')}")
        else:
            fail("G10 经验卡提炼（帷幄工具结构化结果）", f"exec={card_out[0]}")
    else:
        fail("G10 经验卡提炼", "no report artifact")

    # ── 7) 后台任务（§12.3 + §8.8：提交→泵→完成事件） ────────────────────
    task = _call("POST", "/command/tasks",
                 {"tool_name": "build_pit_snapshot",
                  "arguments": {"instrument_id": instrument_id},
                  "command_session_id": sid})[1]["task"]
    _call("POST", "/tasks/scheduler/tick")
    time.sleep(1)
    _call("POST", "/tasks/scheduler/tick")
    _, tasks = _call("GET", f"/command/tasks?command_session_id={sid}")
    done = next((t for t in tasks["results"] if t["task_id"] == task["task_id"]), {})
    if done.get("status") == "succeeded" and done.get("progress") == 100:
        ok("G11 后台任务跑道（queued→pump→succeeded 100%）",
           f"status={done.get('status')} progress={done.get('progress')}")
    else:
        fail("G11 后台任务跑道（queued→pump→succeeded 100%）",
             f"status={done.get('status')} progress={done.get('progress')}")
    _, ev3 = _call("GET", f"/command/sessions/{sid}/events")
    types3 = [e["event_type"] for e in ev3["results"]]
    if "task_started" in types3 and "task_completed" in types3:
        ok("G12 任务事件进会话流（通知）", "")
    else:
        fail("G12 任务事件进会话流（通知）", f"types3={types3}")

    # ── 8) 会话隔离（第二会话不见第一会话的 Workbench） ───────────────────
    _, body2 = _call("POST", "/command/sessions")
    sid2 = body2["session"]["session_id"]
    _, wb2 = _call("GET", f"/command/sessions/{sid2}/workbench")
    if wb2["tabs"] == []:
        ok("G13 会话隔离（第二会话 Workbench 为空）", f"sid2={sid2}")
    else:
        fail("G13 会话隔离（第二会话 Workbench 为空）", f"tabs={len(wb2['tabs'])}")

    # ── 汇总 ────────────────────────────────────────────────────────────
    passed = sum(1 for _, _, ok_ in STEPS if ok_)
    total = len(STEPS)
    report = [
        "# F14-WEIWO-GOLDEN — 帷幄跨模块闭环证据（§12.3）", "",
        "> live compose 栈全程 API 驱动；000831 中国稀土。", "",
        f"## 汇总：{passed}/{total} PASS", "",
    ]
    for step, detail, ok_ in STEPS:
        report.append(f"- {'PASS' if ok_ else 'FAIL'} · {step} · {str(detail)[:120]}")
    try:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
    except OSError:
        pass
    print(f"\n=== {passed}/{total} PASS ===", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
