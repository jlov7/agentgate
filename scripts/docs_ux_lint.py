#!/usr/bin/env python3
"""Lightweight UX content lint for docs and interactive shell assets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KEY_PAGES = [
    "HOSTED_SANDBOX.md",
    "DEMO_LAB.md",
    "REPLAY_LAB.md",
    "INCIDENT_RESPONSE.md",
    "TENANT_ROLLOUTS.md",
    "TRY_NOW.md",
    "OPERATIONAL_TRUST_LAYER.md",
]

VERB_PREFIXES = (
    "Start",
    "Run",
    "Open",
    "View",
    "Generate",
    "Move",
    "Apply",
    "Promote",
    "Practice",
    "Confirm",
    "Pick",
    "Validate",
    "Export",
    "Continue",
    "Choose",
)

ERROR_MESSAGE_MARKERS = (
    "what happened",
    "how to fix",
)

JARGON_TERMS = (
    "rego",
    "blast radius",
    "quarantine",
    "canary",
    "rollback",
    "slo",
)

JS_FILES = [
    ROOT / "docs" / "javascripts" / "hosted-sandbox.js",
    ROOT / "docs" / "javascripts" / "demo-lab.js",
    ROOT / "docs" / "javascripts" / "workflow-shell.js",
]


def _find_cta_candidates(text: str) -> list[str]:
    matches = re.findall(r"\[([^\]]+)\]\([^\)]+\)", text)
    return [entry.strip() for entry in matches if entry.strip()]


def _starts_with_verb(value: str) -> bool:
    return any(value.startswith(prefix + " ") or value == prefix for prefix in VERB_PREFIXES)


def _first_body_paragraph(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for line in lines:
        if (
            not line
            or line.startswith("#")
            or line.startswith("<")
            or line.startswith("- ")
            or line.startswith("```")
        ):
            continue
        return line
    return ""


def run_checks() -> dict[str, object]:
    errors: list[str] = []

    for page_name in KEY_PAGES:
        page_path = ROOT / "docs" / page_name
        page_text = page_path.read_text(encoding="utf-8")
        lowered = page_text.lower()

        if "quick start" not in lowered:
            errors.append(f"{page_name}: missing quick-start summary heading or phrase")

        for cta in _find_cta_candidates(page_text):
            if not _starts_with_verb(cta):
                errors.append(f"{page_name}: CTA should start with verb: '{cta}'")

        first_paragraph = _first_body_paragraph(page_text)
        if first_paragraph and len(first_paragraph.split()) > 30:
            word_count = len(first_paragraph.split())
            errors.append(
                f"{page_name}: intro paragraph too long for quick scan ({word_count} words)"
            )

        jargon_hits = sum(1 for term in JARGON_TERMS if term in lowered)
        if jargon_hits > 8:
            errors.append(f"{page_name}: jargon density too high ({jargon_hits} terms)")

    for js_path in JS_FILES:
        js_text = js_path.read_text(encoding="utf-8").lower()
        for marker in ERROR_MESSAGE_MARKERS:
            if marker not in js_text:
                errors.append(f"{js_path.name}: missing standardized error marker '{marker}'")

    return {
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint UX docs hierarchy and CTA conventions.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    result = run_checks()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if result["status"] == "fail":
        for error in result["errors"]:
            print(error)
        return 1

    print("docs ux lint: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
