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


def test_cli_demo_runs_asyncio(monkeypatch) -> None:
    called: dict[str, object] = {}

    async def fake_demo() -> None:
        called["demo"] = True

    def fake_run(coro) -> None:
        called["coro"] = coro
        coro.close()

    monkeypatch.setattr("agentgate.__main__.run_demo", fake_demo)
    monkeypatch.setattr("agentgate.__main__.asyncio.run", fake_run)
    monkeypatch.setattr(sys, "argv", ["agentgate", "--demo"])
    main()
    assert called.get("coro")


def test_cli_runs_uvicorn(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyUvicorn:
        @staticmethod
        def run(app: str, host: str, port: int, reload: bool) -> None:
            captured["app"] = app
            captured["host"] = host
            captured["port"] = port
            captured["reload"] = reload

    monkeypatch.setitem(sys.modules, "uvicorn", DummyUvicorn)
    monkeypatch.setattr(sys, "argv", ["agentgate", "--host", "127.0.0.1", "--port", "9001"])
    main()
    assert captured == {
        "app": "agentgate.main:app",
        "host": "127.0.0.1",
        "port": 9001,
        "reload": False,
    }
