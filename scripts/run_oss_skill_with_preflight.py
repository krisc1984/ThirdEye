from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR_SITE = ROOT / ".vendor" / "py312"
API_ROOT = ROOT / "apps" / "api"

if VENDOR_SITE.exists():
    sys.path.insert(0, str(VENDOR_SITE))
sys.path.insert(0, str(API_ROOT))

from app.agents.oss_skill_preflight import maybe_run_oss_skill_preflight


OUTPUT_DIR = ROOT / "data" / "test-reports"
LOG_PATH = OUTPUT_DIR / "oss_skill_preflight_run.log"
RESULT_PATH = OUTPUT_DIR / "oss_skill_preflight_run_result.md"
CONFIG_PATH = ROOT / "data" / "model-providers" / "xunfei.json"
DEFAULT_TARGET_PROJECT = Path(r"D:\python_project\code-review")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run oss-skill with deterministic preflight.")
    parser.add_argument("--target-project", type=Path, default=DEFAULT_TARGET_PROJECT, help="Absolute local project path to distill")
    args = parser.parse_args(argv)
    target_project = args.target_project

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    query = f'请调用 oss-skill 蒸馏 "{target_project}" 项目，并给出测试结论。'
    answer = maybe_run_oss_skill_preflight(query)
    if answer is None:
        print("oss-skill deterministic preflight did not match the request")
        return 1

    safe_stdout = answer.encode("gbk", errors="replace").decode("gbk", errors="replace")
    print(safe_stdout)
    return 0 if "Status: `PASS`" in answer else 1


if __name__ == "__main__":
    raise SystemExit(main())
