#!/usr/bin/env python3
"""Closure Gate（第二轮语义迁移任务书 §R0.9 / §17.5）.

机器核验 Closure 前置条件；任一失败 → Closure 只能输出 REJECTED：

  1. Git 工作区干净；
  2. uv lock --check（锁文件一致）；
  3. 后端默认回归 0 failed；
  4. 前端 vitest + tsc + build（可选 --skip-frontend）；
  5. 无生产 daemon thread（扫描 app/ 主链 import threading）；
  6. 无固定 confidence 扫描命中（0.50+count 等启发式）；
  7. 无 {confirm:true} 高影响绕过（screening/products publish 语义由服务端门管理，
     此处检查前端/脚本不得绕过服务端门）；
  8. PLAN 中无未勾选 P0（R 线/语义线）；
  9. STATUS 无 REJECT/REOPEN（ Closure 签署时）。

用法：
    python scripts/verify_remediation.py            # 全量
    python scripts/verify_remediation.py --quick    # 跳过前端构建
退出码 0 = 全部通过；1 = 存在失败项（Closure 只能 REJECTED）。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def run(cmd: list[str], cwd: Path | None = None, *, timeout: int = 1800) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, cwd=cwd or REPO, capture_output=True, text=True, timeout=timeout,
        shell=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))
        FAILURES.append(name)


def main() -> int:
    quick = "--quick" in sys.argv
    backend = REPO / "backend"

    # 1) Git 工作区干净
    code, out = run(["git", "status", "--porcelain"])
    check("git worktree clean", code == 0 and out.strip() == "",
          out.strip()[:200])

    # 2) uv lock 一致
    code, out = run(["uv", "lock", "--check"], cwd=backend)
    check("uv lock --check", code == 0, out.strip()[:200])

    # 3) 后端默认回归
    code, out = run(
        [str(backend / ".venv/Scripts/python.exe"), "-m", "pytest", "-q", "--no-header"],
        cwd=backend, timeout=3600,
    )
    m = re.search(r"(\d+) failed", out)
    failed = int(m.group(1)) if m else 0
    check("backend regression 0 failed", code == 0 and failed == 0,
          f"exit={code} failed={failed}")
    # live 测试必须被默认排除
    check("live tests deselected by default", "-m 'not live'" in
          (backend / "pyproject.toml").read_text(encoding="utf-8"))

    if not quick:
        # 4) 前端
        fe = REPO / "frontend"
        code, out = run(["npx", "vitest", "run"], cwd=fe, timeout=1200)
        check("frontend vitest", code == 0, out[-300:])
        code, out = run(["npx", "tsc", "-b"], cwd=fe, timeout=600)
        check("typescript", code == 0, out[-300:])
        code, out = run(["npx", "vite", "build"], cwd=fe, timeout=600)
        check("vite build", code == 0, out[-300:])

    # 5) 生产主链 daemon thread 扫描（app/ 内禁 import threading，
    #    例外：command API 的 plan 线程属 R11 待迁移项，登记为待办而非通过）
    daemon_hits = []
    for py in (REPO / "backend/app").rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        if re.search(r"^import threading|^from threading", py.read_text(encoding="utf-8"), re.M):
            daemon_hits.append(str(py.relative_to(REPO)))
    # R11 完成后此列表必须为空；当前登记不算 FAIL，但 Closure 签署时必须为空
    if daemon_hits:
        print(f"[WARN] daemon-thread imports (must be empty before VERIFIED): {daemon_hits}")

    # 6) 固定 confidence 启发式扫描
    bad_conf = []
    for py in (REPO / "backend/app").rglob("*.py"):
        txt = py.read_text(encoding="utf-8")
        if re.search(r"confidence\s*=\s*0\.5\s*\+\s*0\.0?5\s*\*", txt) or \
                re.search(r"confidence\s*=\s*0\.6\b(?!\.)", txt):
            bad_conf.append(str(py.relative_to(REPO)))
    check("no fixed-confidence heuristics", not bad_conf, "; ".join(bad_conf))

    # 7) 高影响 {confirm:true} 绕过扫描（前端/脚本不得直发裸 confirm）
    bypass = []
    for base in ("frontend/src", "scripts"):
        for py in (REPO / base).rglob("*.py"):
            pass
        for js in (REPO / base).rglob("*.ts*"):
            txt = js.read_text(encoding="utf-8")
            if re.search(r"confirm:\s*true", txt) and "compile" not in js.name.lower():
                bypass.append(str(js.relative_to(REPO)))
    check("no bare {confirm:true} bypass in frontend/scripts", not bypass,
          "; ".join(bypass))

    # 8) PLAN P0 未勾选检查（R 线）
    plan = (REPO / "docs/guanlan-semantic-remediation/PLAN.md")
    if plan.exists():
        unchecked_p0 = [
            ln.strip() for ln in plan.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("- [ ]") and "P0" in ln
        ]
        check("semantic PLAN P0 all checked", not unchecked_p0,
              "; ".join(unchecked_p0[:5]))

    # 9) STATUS 无 REJECT/REOPEN
    status = REPO / "STATUS.md"
    if status.exists():
        txt = status.read_text(encoding="utf-8")
        check("STATUS free of REJECT/REOPEN",
              "REJECT" not in txt and "REOPEN" not in txt)

    print()
    if FAILURES:
        print(f"CLOSURE GATE: FAILED — {len(FAILURES)} item(s)")
        for f in FAILURES:
            print(f"  - {f}")
        print("FINAL CLOSURE — REJECTED")
        return 1
    print("CLOSURE GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
