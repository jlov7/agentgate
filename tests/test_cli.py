"""CLI entrypoint tests."""

from __future__ import annotations

import sys

import pytest

from agentgate.__main__ import main


def test_cli_version(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["agentgate", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "AgentGate" in output


def test_cli_help(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["agentgate", "--help"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "usage:" in output.lower()
