#!/usr/bin/env python3
"""Closure 一致性校验（第三轮整改任务书 §4.3 / F1）。

校验 Evidence 汇总数与 Closure 数字一致，杜绝
「Evidence 记 FAIL、Closure 写 PASS」的同一能力冲突。

用法：
    python scripts/check_closure_consistency.py \
        [--evidence docs/research-deep-port/R10-EVIDENCE-V2.md] \
        [--closure docs/research-deep-port/R10-CLOSURE-V2.md]

校验规则：
  R1 Evidence 内部算术：汇总 PASS 数 == PASS 行数，总步数 == 全部行数；
  R2 Closure 的 Golden 数字 == Evidence 汇总数字（不得出现 Evidence 之外的
     更高通过数，如历史遗留 26/26）；
  R3 Evidence 中每个 FAIL 步骤，必须在 Closure 的「未决失败」表中被如实登记；
  R4 Closure Capability Matrix：Real Verify / Golden 列为 FAIL / BLOCKED_* /
     PARTIAL / PLANNED / NOT RUN 的行，Final 列不得为 PASS；
  R5 Closure 全文禁止出现与 Evidence 冲突的旧通过数（如 26/26）。

退出码：0 = 一致；1 = 存在冲突（逐条打印）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_EVIDENCE = REPO / "docs/research-deep-port/R10-EVIDENCE-V2.md"
DEFAULT_CLOSURE = REPO / "docs/research-deep-port/R10-CLOSURE-V2.md"

# `- PASS · step · detail` / `- FAIL · step · detail`
EVIDENCE_STEP = re.compile(r"^-\s+(PASS|FAIL)\s+·\s+(.+?)\s+·", re.M)
EVIDENCE_SUMMARY = re.compile(r"^##\s+汇总：(\d+)/(\d+)\s+PASS\s*$", re.M)
# Closure Golden 行：| Golden E2E | **24/25 PASS...** |（容忍粗体/括注）
GOLDEN_CLAIM = re.compile(r"(\d+)\s*/\s*(\d+)\s*PASS")
# Matrix 行：| Name | PASS | PASS | N/A | PASS | PASS | **PASS** |
MATRIX_ROW = re.compile(
    r"^\|\s*([^|`\n]+?)\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|",
    re.M,
)
NON_PASS_TOKENS = ("FAIL", "BLOCKED", "PARTIAL", "PLANNED", "NOT RUN", "REOPEN")


def parse_evidence(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = EVIDENCE_SUMMARY.search(text)
    if not m:
        return {"error": f"未找到「## 汇总：X/Y PASS」标题：{path}"}
    passed, total = int(m.group(1)), int(m.group(2))
    steps = [(g.group(1), g.group(2).strip()) for g in EVIDENCE_STEP.finditer(text)]
    fail_steps = [name for status, name in steps if status == "FAIL"]
    return {
        "passed": passed,
        "total": total,
        "n_pass": sum(1 for s, _ in steps if s == "PASS"),
        "n_lines": len(steps),
        "fail_steps": fail_steps,
    }


def parse_closure(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {"text": text}


def strip_md(cell: str) -> str:
    return cell.replace("**", "").replace("`", "").strip()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    ap.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    args = ap.parse_args()

    problems: list[str] = []
    ev = parse_evidence(args.evidence)
    cl = parse_closure(args.closure)

    if "error" in ev:
        print(f"[F1-GATE] FAIL: {ev['error']}")
        return 1

    # R1 — Evidence 内部算术
    if ev["n_lines"] != ev["total"] or ev["n_pass"] != ev["passed"]:
        problems.append(
            f"R1 Evidence 汇总数与明细不一致：汇总 {ev['passed']}/{ev['total']}，"
            f"明细 PASS {ev['n_pass']} / 总行 {ev['n_lines']}"
        )
    else:
        print(f"[R1] OK — Evidence 汇总 {ev['passed']}/{ev['total']} 与明细一致")

    # R2 — Closure 的 Golden 表行数字必须等于 Evidence 汇总
    # 只认表格行（| 开头）且含 Golden 的行，避免 SEM-01/02 之类编号误匹配
    golden_line = None
    for line in cl["text"].splitlines():
        s = line.strip()
        if (
            s.startswith("|")
            and "golden" in s.lower()
            and "evidence" not in s.lower()
            and GOLDEN_CLAIM.search(s)
        ):
            golden_line = s
            break
    if golden_line is None:
        problems.append("R2 Closure 未找到 Golden E2E 数字行（| Golden ... | X/Y PASS |）")
    else:
        m = GOLDEN_CLAIM.search(golden_line)
        gp, gt = int(m.group(1)), int(m.group(2))
        if (gp, gt) != (ev["passed"], ev["total"]):
            problems.append(
                f"R2 Closure Golden 数字 {gp}/{gt} 与 Evidence 汇总 "
                f"{ev['passed']}/{ev['total']} 冲突（行：{golden_line.strip()[:80]}）"
            )
        else:
            print(f"[R2] OK — Closure Golden {gp}/{gt} == Evidence 汇总")

    # R3 — Evidence 每个 FAIL 必须登记在 Closure「未决失败」节
    unresolved = cl["text"]
    for fail_step in ev["fail_steps"]:
        # 步骤名取编号前的主体（如 "6b Production Signal API"）
        key = fail_step.strip()
        token = key.split(" ", 1)[-1] if " " in key else key
        if key not in unresolved and token not in unresolved:
            problems.append(f"R3 Evidence FAIL 步骤「{key}」未在 Closure 中如实登记")

    # R4 — Matrix：Real Verify / Golden 非 PASS 的行 Final 不得 PASS
    in_matrix = False
    for line in cl["text"].splitlines():
        if line.strip().startswith("|") and "Capability" in line:
            in_matrix = True
            continue
        if in_matrix:
            if not line.strip().startswith("|"):
                in_matrix = False
                continue
            if set(line.strip()) <= {"|", "-", " ", ":"}:
                continue
            m = MATRIX_ROW.match(line.strip())
            if not m:
                continue
            name = strip_md(m.group(1))
            real_verify, golden, final = (
                strip_md(m.group(5)),
                strip_md(m.group(6)),
                strip_md(m.group(7)),
            )
            if final.upper().startswith("PASS"):
                for label, val in (("Real Verify", real_verify), ("Golden", golden)):
                    if any(tok in val.upper() for tok in NON_PASS_TOKENS):
                        problems.append(
                            f"R4 能力「{name}」{label}={val} 但 Final=PASS"
                        )
            # Golden 列为 FAIL 的行，Final 也不得 PASS

    # R5 — Golden 相关行中残留的旧通过数（含正文的 Golden N/N PASS 声明）。
    # 只扫描含 Golden 的行，且要求总数 >= 10，避免 SEM-01/02 类编号误匹配。
    for line in cl["text"].splitlines():
        if "golden" not in line.lower():
            continue
        for m in GOLDEN_CLAIM.finditer(line):
            gp, gt = int(m.group(1)), int(m.group(2))
            if gt >= 10 and (gp, gt) != (ev["passed"], ev["total"]):
                problems.append(
                    f"R5 Golden 行残留冲突通过数 {gp}/{gt}"
                    f"（Evidence 汇总为 {ev['passed']}/{ev['total']}）"
                )
                break

    if problems:
        print(f"[F1-GATE] FAIL — {len(problems)} 处冲突：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[F1-GATE] PASS — Evidence 与 Closure 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
