"""CI workflow regression tests."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_workflow() -> dict:
    workflow_path = Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def test_ci_uses_concurrency_control() -> None:
    workflow = _load_workflow()
    concurrency = workflow["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "github.workflow" in concurrency["group"]


def test_ci_installs_python_dependencies_from_lockfile() -> None:
    workflow = _load_workflow()
    jobs = workflow["jobs"]

    for job_name in ("lint", "verify", "security", "sbom", "load-test", "verify-strict"):
        job = jobs[job_name]
        install_step = next(
            step for step in job["steps"] if step["name"] == "Install Python dependencies"
        )
        assert "scripts/install_python_deps.sh" in install_step["run"]
        assert "requirements/dev.lock" in install_step["run"]


def test_verify_strict_job_runs_for_prs_pushes_and_weekly_schedule() -> None:
    workflow = _load_workflow()
    strict_job = workflow["jobs"]["verify-strict"]
    strict_condition = "github.event_name != 'schedule' || github.event.schedule == '47 3 * * 0'"
    assert strict_job["if"] == strict_condition

    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    schedule_entries = on_section["schedule"]
    assert {"cron": "47 3 * * 0"} in schedule_entries

    run_step = next(step for step in strict_job["steps"] if step["name"] == "Run mutation gate")
    assert run_step["run"] == "make mutate"


def test_load_test_p95_budget_is_not_too_strict() -> None:
    workflow = _load_workflow()

    load_test_job = workflow["jobs"]["load-test"]
    assert "if" not in load_test_job

    load_test_steps = load_test_job["steps"]
    run_load_test_step = next(step for step in load_test_steps if step["name"] == "Run load test")
    load_test_env = run_load_test_step["env"]
    assert int(load_test_env["LOAD_VUS"]) <= 30
    assert int(load_test_env["LOAD_DURATION"].rstrip("s")) <= 30
    assert int(load_test_env["LOAD_RAMP_UP"].rstrip("s")) <= 10
    assert int(load_test_env["LOAD_RAMP_DOWN"].rstrip("s")) <= 10
    assert int(load_test_env["LOAD_P95"]) >= 2000
    assert load_test_env["LOAD_TEST_SUMMARY"] == "reports/load-test-summary.json"
    assert "continue-on-error" not in run_load_test_step

    upload_summary_step = next(
        step for step in load_test_steps if step["name"] == "Upload load test summary"
    )
    assert upload_summary_step["if"] == "always()"

    upload_summary_artifact_step = next(
        step for step in load_test_steps if step["name"] == "Upload load test summary artifact"
    )
    assert upload_summary_artifact_step["if"] == "always()"
