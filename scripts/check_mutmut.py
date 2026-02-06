"""Validate mutmut results against a minimum score."""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from collections.abc import Mapping


THRESHOLD = 1.0
ALLOWED_STATUSES = {"killed", "survived"}


def parse_status_counts(output: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        status = line.split(":", 1)[1].strip()
        if status:
            counts[status] += 1
    return counts


def score_mutations(counts: Mapping[str, int]) -> tuple[int, int, float]:
    killed = counts.get("killed", 0)
    survived = counts.get("survived", 0)
    total = killed + survived
    score = killed / total if total else 1.0
    return killed, survived, score


def main() -> int:
    output = subprocess.check_output(
        [".venv/bin/mutmut", "results", "--all", "true"], text=True
    )
    counts = parse_status_counts(output)
    unexpected = {status: count for status, count in counts.items() if status not in ALLOWED_STATUSES}
    if unexpected:
        print(
            f"unexpected mutmut statuses: {unexpected}. "
            "Fix mutation runtime instability before enforcing score.",
            file=sys.stderr,
        )
        return 1

    killed, survived, score = score_mutations(counts)
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
