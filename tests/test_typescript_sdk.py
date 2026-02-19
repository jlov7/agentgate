"""TypeScript SDK verification tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_DIR = ROOT / "sdk" / "typescript"


def test_typescript_sdk_node_tests_pass() -> None:
    node_bin = shutil.which("node")
    assert node_bin is not None
    result = subprocess.run(  # noqa: S603
        [node_bin, "--test", "tests/client.test.mjs"],
        cwd=SDK_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        output = f"{result.stdout}\n{result.stderr}".strip()
        raise AssertionError(output)


def test_typescript_sdk_declares_types_entrypoint() -> None:
    declaration = SDK_DIR / "src" / "index.d.ts"
    package_json = (SDK_DIR / "package.json").read_text(encoding="utf-8")

    assert declaration.exists()
    assert '"types": "./src/index.d.ts"' in package_json
    assert "class AgentGateClient" in declaration.read_text(encoding="utf-8")
