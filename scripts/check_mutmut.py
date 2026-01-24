"""Validate mutmut results against a minimum score."""

from __future__ import annotations

import subprocess
import sys


THRESHOLD = 0.85


def main() -> int:
    output = subprocess.check_output(
        [".venv/bin/mutmut", "results", "--all", "true"], text=True
    )
    killed = 0
    survived = 0
    for line in output.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        status = line.split(":", 1)[1].strip()
        if status == "killed":
            killed += 1
        else:
            survived += 1

    total = killed + survived
    score = killed / total if total else 1.0
    print(f"mutmut: killed={killed} survived={survived} score={score:.3f}")

    if score < THRESHOLD:
        print(
            f"mutation score {score:.3f} below {THRESHOLD:.2f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
