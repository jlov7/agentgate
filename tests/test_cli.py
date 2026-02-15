"""CLI entrypoint tests."""

from __future__ import annotations

import json
import runpy
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


def test_cli_showcase_uses_timestamped_default_session(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            return cls()

        def strftime(self, fmt: str) -> str:
            return "20260214T000000Z"

    async def fake_showcase(config) -> int:
        captured["session_id"] = config.session_id
        return 0

    monkeypatch.setattr("agentgate.__main__.datetime", FakeDateTime)
    monkeypatch.setattr("agentgate.showcase.run_showcase", fake_showcase)
    monkeypatch.setattr(sys, "argv", ["agentgate", "--showcase"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert captured["session_id"] == "showcase-20260214T000000Z"


def test_cli_showcase_respects_explicit_session(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_showcase(config) -> int:
        captured["session_id"] = config.session_id
        return 0

    monkeypatch.setattr("agentgate.showcase.run_showcase", fake_showcase)
    monkeypatch.setattr(
        sys,
        "argv",
        ["agentgate", "--showcase", "--showcase-session", "showcase-explicit"],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert captured["session_id"] == "showcase-explicit"


def test_cli_showcase_respects_explicit_showcase_session(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_showcase(config) -> int:
        captured["session_id"] = config.session_id
        return 0

    monkeypatch.setattr("agentgate.showcase.run_showcase", fake_showcase)
    monkeypatch.setattr(
        sys,
        "argv",
        ["agentgate", "--showcase", "--showcase-session", "showcase"],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert captured["session_id"] == "showcase"


def test_cli_can_trigger_replay_and_print_summary_json(capsys, monkeypatch, tmp_path) -> None:
    payload = {
        "session_id": "cli-session",
        "baseline_policy_version": "v1",
        "candidate_policy_version": "v2",
        "baseline_policy_data": {"read_only_tools": ["db_query"]},
        "candidate_policy_data": {"read_only_tools": []},
    }
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    class DummyClient:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def create_replay_run(self, *, api_key: str, payload: dict) -> dict:
            return {"run_id": "run-cli", "summary": {"total_events": 0}}

    monkeypatch.setattr("agentgate.__main__.AgentGateClient", DummyClient)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agentgate",
            "--replay-run",
            str(path),
            "--admin-key",
            "admin",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "\"run_id\": \"run-cli\"" in output


def test_cli_can_release_incident_and_show_status(capsys, monkeypatch) -> None:
    class DummyClient:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def release_incident(
            self,
            *,
            api_key: str,
            incident_id: str,
            released_by: str,
        ) -> dict:
            return {"status": "released", "incident_id": incident_id}

    monkeypatch.setattr("agentgate.__main__.AgentGateClient", DummyClient)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agentgate",
            "--incident-release",
            "incident-123",
            "--released-by",
            "ops",
            "--admin-key",
            "admin",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "\"status\": \"released\"" in output


def test_main_module_runs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyUvicorn:
        @staticmethod
        def run(app: str, host: str, port: int, reload: bool) -> None:
            captured["app"] = app
            captured["host"] = host
            captured["port"] = port
            captured["reload"] = reload

    monkeypatch.setitem(sys.modules, "uvicorn", DummyUvicorn)
    monkeypatch.setattr(sys, "argv", ["agentgate"])

    prior_main = sys.modules.pop("agentgate.__main__", None)
    try:
        runpy.run_module("agentgate.__main__", run_name="__main__")
    finally:
        if prior_main is not None:
            sys.modules["agentgate.__main__"] = prior_main

    assert captured["host"] == "0.0.0.0"  # noqa: S104
