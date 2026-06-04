from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR_SITE = ROOT / ".vendor" / "py312"
API_ROOT = ROOT / "apps" / "api"

if VENDOR_SITE.exists():
    sys.path.insert(0, str(VENDOR_SITE))
sys.path.insert(0, str(API_ROOT))

from scripts.skill_agent import create_openai_agent_with_skills


OUTPUT_DIR = ROOT / "data" / "test-reports"
LOG_PATH = OUTPUT_DIR / "oss_skill_real_run.log"
RESULT_PATH = OUTPUT_DIR / "oss_skill_real_run_result.md"
CONFIG_PATH = ROOT / "data" / "model-providers" / "xunfei.json"
TARGET_PROJECT = r"D:\python_project\code-review"


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    query = (
        f'请调用 oss-skill 蒸馏 "{TARGET_PROJECT}" 项目。'
        "先检查可用 skills，加载 oss-skill，然后给出针对该项目的蒸馏执行方案、"
        "需要读取的材料、以及你会如何验证 agent 调用复杂 skill 的可用性。"
    )

    logs: list[str] = []

    def log(message: str) -> None:
        line = f"[{_ts()}] {message}"
        print(line)
        logs.append(line)

    log("Start real oss-skill run")
    log(f"Provider: {config['id']} / {config['model']}")
    log(f"Target project: {TARGET_PROJECT}")

    agent, loader, tools = create_openai_agent_with_skills(
        api_key=config.get("api_key"),
        base_url=config.get("base_url"),
        model=config.get("model"),
        skills_dir=API_ROOT / "skills",
        workdir=ROOT,
        allowed_roots=[ROOT, Path(TARGET_PROJECT)],
    )
    log(f"Loaded skills: {', '.join(loader.list_skills())}")
    log(f"Available tools: {', '.join(tool['function']['name'] for tool in tools)}")

    try:
        answer = agent.chat(query, max_turns=20)
        log("Real run completed")
        status = "PASS"
    except Exception as error:
        answer = f"Agent run failed: {error}"
        log(f"Real run failed: {error}")
        status = "FAIL"

    LOG_PATH.write_text("\n".join(logs) + "\n", encoding="utf-8")
    RESULT_PATH.write_text(
        "\n".join(
            [
                "# OSS Skill Real Run Result",
                "",
                f"- Time: {_ts()}",
                f"- Provider: `{config['id']}` / `{config['model']}`",
                f"- Target project: `{TARGET_PROJECT}`",
                f"- Status: `{status}`",
                "",
                "## Query",
                "",
                query,
                "",
                "## Response",
                "",
                answer,
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(answer)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
