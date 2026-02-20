"""Tests for mutation score validation helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_mutmut.py"
_SPEC = importlib.util.spec_from_file_location("check_mutmut", _SCRIPT_PATH)
assert _SPEC and _SPEC.loader
check_mutmut = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_mutmut)


def test_parse_status_counts_tracks_each_status() -> None:
    output = "\n".join(
        [
            "pkg.mod.mut_1: killed",
            "pkg.mod.mut_2: survived",
            "pkg.mod.mut_3: segfault",
            "noise line",
            "",
        ]
    )
    counts = check_mutmut.parse_status_counts(output)

    assert counts["killed"] == 1
    assert counts["survived"] == 1
    assert counts["segfault"] == 1


def test_main_fails_for_unexpected_statuses(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        check_mutmut.subprocess,
        "check_output",
        lambda *args, **kwargs: "pkg.mod.mut_1: segfault\n",
    )

    exit_code = check_mutmut.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "unexpected mutmut statuses" in captured.err


def test_main_fails_when_score_below_threshold(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENTGATE_MUTATION_MIN_SCORE", "1.0")
    monkeypatch.setattr(
        check_mutmut.subprocess,
        "check_output",
        lambda *args, **kwargs: "pkg.mod.mut_1: survived\n",
    )

    exit_code = check_mutmut.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "below 1.00" in captured.err


def test_main_passes_on_all_killed(monkeypatch) -> None:
    monkeypatch.setattr(
        check_mutmut.subprocess,
        "check_output",
        lambda *args, **kwargs: "pkg.mod.mut_1: killed\npkg.mod.mut_2: killed\n",
    )

    assert check_mutmut.main() == 0


def test_main_rejects_invalid_threshold_env(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AGENTGATE_MUTATION_MIN_SCORE", "not-a-number")

    exit_code = check_mutmut.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "AGENTGATE_MUTATION_MIN_SCORE must be a float between 0 and 1" in captured.err
