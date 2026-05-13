from pathlib import Path

from app.agents import oss_skill_preflight


def test_oss_skill_query_routes_to_preflight(monkeypatch, tmp_path: Path):
    target = tmp_path / "code-review"
    target.mkdir()
    (target / "README.md").write_text("# demo\n", encoding="utf-8")
    (target / "pom.xml").write_text("<project />\n", encoding="utf-8")
    monkeypatch.setattr(oss_skill_preflight, "DEFAULT_REPORT_DIR", tmp_path)
    monkeypatch.setattr(oss_skill_preflight, "DEFAULT_LOG_PATH", tmp_path / "oss_skill_preflight_run.log")
    monkeypatch.setattr(oss_skill_preflight, "DEFAULT_REPORT_PATH", tmp_path / "oss_skill_preflight_run_result.md")

    result = oss_skill_preflight.maybe_run_oss_skill_preflight(
        '请调用 oss-skill 蒸馏 "D:\\python_project\\code-review" 项目，并给出测试结论。'
    )

    patched_result = oss_skill_preflight.maybe_run_oss_skill_preflight(
        f'请调用 oss-skill 蒸馏 "{target}" 项目，并给出测试结论。'
    )

    assert result is not None
    assert patched_result is not None
    assert "OSS Skill Preflight Run Result" in patched_result
    assert "deterministic preflight" in patched_result
    assert str(target) in patched_result
