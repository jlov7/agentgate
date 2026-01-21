"""Run adversarial tests and emit a simple JSON report."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    """Run adversarial tests and return the exit code."""
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / "adversarial_report.json"

    cmd = [sys.executable, "-m", "pytest", "tests/adversarial", "-v"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": " ".join(cmd),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
