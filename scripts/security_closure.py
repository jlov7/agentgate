#!/usr/bin/env python3
"""Build an external security-assessment closure artifact."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pip-audit",
        type=Path,
        default=Path("artifacts/pip-audit.json"),
        help="Path to pip-audit JSON report.",
    )
    parser.add_argument(
        "--bandit",
        type=Path,
        default=Path("artifacts/bandit.json"),
        help="Path to Bandit JSON report.",
    )
    parser.add_argument(
        "--sbom",
        type=Path,
        default=Path("reports/sbom.json"),
        help="Path to CycloneDX SBOM JSON report.",
    )
    parser.add_argument(
        "--assessment",
        type=Path,
        default=Path("security/external-assessment-findings.json"),
        help="Path to external security assessment findings JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/security-closure.json"),
        help="Path to write security closure artifact JSON.",
    )
    return parser.parse_args()


def _load_json(path: Path, label: str, findings: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        findings.append(f"{label} file not found: {path}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(f"{label} JSON invalid: {exc}")
        return None
    if not isinstance(payload, dict):
        findings.append(f"{label} payload must be a JSON object.")
        return None
    return payload


def _count_pip_audit_vulnerabilities(payload: dict[str, Any]) -> int:
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, list):
        return 0
    count = 0
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        vulns = dependency.get("vulns")
        if isinstance(vulns, list):
            count += len(vulns)
    return count


def _count_bandit_findings(payload: dict[str, Any]) -> int:
    results = payload.get("results")
    if not isinstance(results, list):
        return 0
    return len(results)


def _count_sbom_components(payload: dict[str, Any]) -> int:
    components = payload.get("components")
    if not isinstance(components, list):
        return 0
    return len(components)


def _evaluate_assessment(payload: dict[str, Any], findings: list[str]) -> dict[str, int]:
    assessment_findings = payload.get("findings")
    if not isinstance(assessment_findings, list):
        findings.append("Assessment report missing findings list.")
        return {
            "total": 0,
            "open": 0,
            "closed": 0,
            "risk_accepted": 0,
        }

    totals = {
        "total": 0,
        "open": 0,
        "closed": 0,
        "risk_accepted": 0,
    }

    for item in assessment_findings:
        if not isinstance(item, dict):
            continue
        totals["total"] += 1
        finding_id = str(item.get("id", "unknown"))
        status = str(item.get("status", "")).strip().lower()
        if status == "closed":
            totals["closed"] += 1
            continue
        if status == "risk_accepted":
            approved_by = str(item.get("approved_by", "")).strip()
            rationale = str(item.get("rationale", "")).strip()
            if approved_by and rationale:
                totals["risk_accepted"] += 1
            else:
                totals["open"] += 1
                findings.append(
                    f"Assessment finding {finding_id} risk_accepted without approved_by/rationale."
                )
            continue
        totals["open"] += 1
        findings.append(
            f"Assessment finding {finding_id} remains open "
            f"(status={status or 'unknown'})."
        )

    return totals


def run() -> int:
    args = _parse_args()
    findings: list[str] = []

    pip_audit_payload = _load_json(args.pip_audit, "pip-audit report", findings)
    bandit_payload = _load_json(args.bandit, "Bandit report", findings)
    sbom_payload = _load_json(args.sbom, "SBOM report", findings)
    assessment_payload = _load_json(args.assessment, "Assessment report", findings)

    pip_audit_vulnerabilities = (
        _count_pip_audit_vulnerabilities(pip_audit_payload) if pip_audit_payload else 0
    )
    if pip_audit_payload and pip_audit_vulnerabilities > 0:
        findings.append(f"pip-audit reported {pip_audit_vulnerabilities} vulnerabilities.")

    bandit_findings = _count_bandit_findings(bandit_payload) if bandit_payload else 0
    if bandit_payload and bandit_findings > 0:
        findings.append(f"Bandit reported {bandit_findings} findings.")

    sbom_components = _count_sbom_components(sbom_payload) if sbom_payload else 0
    if sbom_payload and sbom_components == 0:
        findings.append("SBOM has zero components.")

    assessment_summary = (
        _evaluate_assessment(assessment_payload, findings)
        if assessment_payload
        else {"total": 0, "open": 0, "closed": 0, "risk_accepted": 0}
    )

    status = "pass" if not findings else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "inputs": {
            "pip_audit": str(args.pip_audit),
            "bandit": str(args.bandit),
            "sbom": str(args.sbom),
            "assessment": str(args.assessment),
        },
        "summary": {
            "pip_audit_vulnerabilities": pip_audit_vulnerabilities,
            "bandit_findings": bandit_findings,
            "sbom_components": sbom_components,
            "assessment_total_findings": assessment_summary["total"],
            "assessment_open_findings": assessment_summary["open"],
            "assessment_closed_findings": assessment_summary["closed"],
            "assessment_risk_accepted_findings": assessment_summary["risk_accepted"],
        },
        "findings": findings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"security closure report: {args.output}")
    print(f"status: {status}")

    return 0 if status == "pass" else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
