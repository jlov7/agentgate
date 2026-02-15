#!/usr/bin/env python3
"""Run a polished first-run AgentGate experience and package proof artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from agentgate.showcase import ShowcaseConfig, run_showcase

OPTIONAL_SUPPORT_ARTIFACTS = (
    "artifacts/replay-report.json",
    "artifacts/incident-report.json",
    "artifacts/rollout-report.json",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="AgentGate base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/showcase"),
        help="Directory for showcase/proof artifacts (default: docs/showcase)",
    )
    parser.add_argument(
        "--session-prefix",
        default="try",
        help="Session prefix for generated showcase session IDs (default: try)",
    )
    parser.add_argument(
        "--approval-token",
        default="approved",
        help="Approval token used in showcase write step (default: approved)",
    )
    parser.add_argument(
        "--theme",
        default="dark",
        help="Evidence theme for showcase HTML/PDF export (default: dark)",
    )
    parser.add_argument(
        "--light-theme",
        default="light",
        help="Alternate evidence theme for light export (default: light)",
    )
    parser.add_argument(
        "--bundle-name",
        default="proof-bundle-{session_id}.zip",
        help="Bundle filename template (default: proof-bundle-{session_id}.zip)",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Optional summary.json path. If set, skips showcase run and only builds proof bundle.",
    )
    return parser.parse_args()


def _session_id(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def _read_summary(summary_path: Path) -> dict[str, Any]:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("summary payload must be a JSON object")
    return payload


def _resolve_bundle_name(template: str, session_id: str) -> str:
    try:
        return template.format(session_id=session_id)
    except KeyError as exc:  # pragma: no cover - defensive parsing guard
        raise ValueError(f"invalid bundle-name template key: {exc}") from exc


def _artifact_candidates(summary: dict[str, Any], summary_path: Path) -> list[Path]:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}

    candidates: list[Path] = [summary_path]
    for value in artifacts.values():
        if isinstance(value, str):
            path = Path(value)
            if not path.is_absolute():
                cwd_candidate = (Path.cwd() / path).resolve()
                summary_candidate = (summary_path.parent / path).resolve()
                path = cwd_candidate if cwd_candidate.exists() else summary_candidate
            candidates.append(path)

    repo_root = Path.cwd()
    for artifact in OPTIONAL_SUPPORT_ARTIFACTS:
        candidates.append((repo_root / artifact).resolve())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def _bundle_manifest(*, summary: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "session_id": summary.get("session_id", "unknown"),
        "status": summary.get("status", "unknown"),
        "files": [str(path) for path in files],
    }


def _write_proof_bundle(
    bundle_path: Path,
    summary: dict[str, Any],
    summary_path: Path,
) -> list[Path]:
    files = [path for path in _artifact_candidates(summary, summary_path) if path.exists()]
    manifest = _bundle_manifest(summary=summary, files=files)

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(bundle_path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        for file_path in files:
            try:
                arcname = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                arcname = file_path.name
            archive.write(file_path, arcname=arcname)
    return files


def _print_report(
    *,
    summary: dict[str, Any],
    summary_path: Path,
    bundle_path: Path,
    files: list[Path],
) -> None:
    session_id = str(summary.get("session_id", "unknown"))
    status = str(summary.get("status", "unknown")).upper()

    print(f"Try run status: {status}")
    print(f"Session ID: {session_id}")
    print("")
    print("Open these now:")
    print(f"- Summary: file://{summary_path.resolve()}")

    artifacts = summary.get("artifacts")
    if isinstance(artifacts, dict):
        evidence_html = artifacts.get("evidence_html")
        metrics = artifacts.get("metrics")
        showcase_log = artifacts.get("showcase_log")
        if isinstance(evidence_html, str):
            print(f"- Evidence: file://{Path(evidence_html).resolve()}")
        if isinstance(metrics, str):
            print(f"- Metrics: file://{Path(metrics).resolve()}")
        if isinstance(showcase_log, str):
            print(f"- Narrated log: file://{Path(showcase_log).resolve()}")

    print(f"- Proof bundle: file://{bundle_path.resolve()}")
    print("")
    print(f"Bundled files: {len(files)}")


def run() -> int:
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = args.summary_path.resolve() if args.summary_path else output_dir / "summary.json"

    if args.summary_path is None:
        session_id = _session_id(args.session_prefix)
        config = ShowcaseConfig(
            base_url=args.base_url,
            output_dir=output_dir,
            session_id=session_id,
            approval_token=args.approval_token,
            step_delay=0,
            evidence_theme=args.theme,
            light_theme=args.light_theme,
        )
        exit_code = asyncio.run(run_showcase(config))
        if exit_code != 0:
            print(
                "Showcase run failed. Review the generated summary/log for details:",
                file=sys.stderr,
            )
            print(f"- file://{summary_path.resolve()}", file=sys.stderr)
            return exit_code

    if not summary_path.exists():
        print(f"Missing summary file: {summary_path}", file=sys.stderr)
        return 1

    summary = _read_summary(summary_path)
    session_id = str(summary.get("session_id", "unknown"))
    bundle_name = _resolve_bundle_name(args.bundle_name, session_id)
    bundle_path = output_dir / bundle_name
    files = _write_proof_bundle(bundle_path, summary, summary_path)
    _print_report(summary=summary, summary_path=summary_path, bundle_path=bundle_path, files=files)
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
