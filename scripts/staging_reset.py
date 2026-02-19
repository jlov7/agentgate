#!/usr/bin/env python3
"""Reset staging data and seed deterministic validation scenarios."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("STAGING_URL", ""),
        help="Staging base URL (defaults to STAGING_URL).",
    )
    parser.add_argument(
        "--admin-key",
        default=os.getenv("AGENTGATE_ADMIN_API_KEY", ""),
        help="Admin API key (defaults to AGENTGATE_ADMIN_API_KEY).",
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path("deploy/staging/seed_scenarios.json"),
        help="Seed scenarios JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/staging-reset.json"),
        help="Path to write reset summary.",
    )
    return parser.parse_args()


def _load_seed_scenarios(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Seed file must contain a JSON list.")

    scenarios: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Seed scenario #{index} must be an object.")
        scenario_id = item.get("id")
        request = item.get("request")
        expected_success = item.get("expected_success")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError(f"Seed scenario #{index} missing string id.")
        if not isinstance(request, dict):
            raise ValueError(f"Seed scenario '{scenario_id}' missing request object.")
        if not isinstance(expected_success, bool):
            raise ValueError(f"Seed scenario '{scenario_id}' missing boolean expected_success.")
        scenarios.append(item)
    return scenarios


def run_reset(
    *,
    base_url: str,
    admin_key: str,
    seed_file: Path,
    now: datetime,
    client: Any | None = None,
) -> dict[str, Any]:
    scenarios = _load_seed_scenarios(seed_file)
    normalized_base_url = base_url.rstrip("/")
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20.0)

    try:
        purge_response = http_client.post(
            f"{normalized_base_url}/admin/sessions/purge",
            headers={"X-API-Key": admin_key},
            json={"purge_before": now.isoformat()},
        )
        purge_response.raise_for_status()
        purge_payload = purge_response.json()
        if not isinstance(purge_payload, dict):
            raise ValueError("Purge endpoint returned non-object payload.")

        scenario_results: list[dict[str, Any]] = []
        failed = 0
        for scenario in scenarios:
            scenario_id = str(scenario["id"])
            expected_success = bool(scenario["expected_success"])
            response = http_client.post(
                f"{normalized_base_url}/tools/call",
                json=scenario["request"],
            )
            payload: dict[str, Any] = {}
            try:
                parsed = response.json()
                if isinstance(parsed, dict):
                    payload = parsed
            except Exception:
                payload = {}

            actual_success = response.status_code == 200 and bool(payload.get("success"))
            matched = actual_success == expected_success
            if not matched:
                failed += 1

            scenario_results.append(
                {
                    "id": scenario_id,
                    "expected_success": expected_success,
                    "actual_success": actual_success,
                    "status_code": response.status_code,
                    "matched_expectation": matched,
                }
            )

        return {
            "generated_at": now.isoformat(),
            "status": "pass" if failed == 0 else "fail",
            "purge": {
                "purged_count": int(purge_payload.get("purged_count", 0)),
                "purged_sessions": purge_payload.get("purged_sessions", []),
            },
            "seed": {
                "total": len(scenarios),
                "failed": failed,
                "results": scenario_results,
            },
        }
    finally:
        if owns_client:
            close = getattr(http_client, "close", None)
            if callable(close):
                close()


def main() -> int:
    args = _parse_args()
    if not args.base_url:
        raise SystemExit("Missing staging base URL. Set --base-url or STAGING_URL.")
    if not args.admin_key:
        raise SystemExit("Missing admin key. Set --admin-key or AGENTGATE_ADMIN_API_KEY.")
    if not args.seed_file.exists():
        raise SystemExit(f"Seed file not found: {args.seed_file}")

    summary = run_reset(
        base_url=args.base_url,
        admin_key=args.admin_key,
        seed_file=args.seed_file,
        now=datetime.now(UTC),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"staging reset report: {args.output}")
    print(f"status: {summary['status']}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
