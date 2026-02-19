"""PII redaction/tokenization helpers."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

_SUPPORTED_MODES = {"off", "redact", "tokenize"}
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"\+?\d[\d\-\s()]{7,}\d")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


def get_pii_mode() -> str:
    """Return normalized PII handling mode."""
    raw = os.getenv("AGENTGATE_PII_MODE", "off").strip().lower()
    return raw if raw in _SUPPORTED_MODES else "off"


def _tokenize(label: str, value: str, *, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{label}:{value}".encode()).hexdigest()
    return f"tok_{label}_{digest[:12]}"


def scrub_text(value: str, *, mode: str | None = None) -> str:
    """Redact/tokenize PII-like substrings inside text."""
    effective_mode = mode if mode in _SUPPORTED_MODES else get_pii_mode()
    if effective_mode == "off" or not value:
        return value

    salt = os.getenv("AGENTGATE_PII_TOKEN_SALT", "")
    scrubbed = value
    for label, pattern in _PATTERNS:
        if effective_mode == "redact":
            scrubbed = pattern.sub(f"[REDACTED_{label.upper()}]", scrubbed)
            continue
        def _replace(match: re.Match[str], pii_label: str = label) -> str:
            return _tokenize(pii_label, match.group(0), salt=salt)
        scrubbed = pattern.sub(
            _replace,
            scrubbed,
        )
    return scrubbed


def scrub_value(value: Any, *, mode: str | None = None) -> Any:
    """Recursively scrub scalar strings, lists, and dictionaries."""
    if isinstance(value, str):
        return scrub_text(value, mode=mode)
    if isinstance(value, list):
        return [scrub_value(item, mode=mode) for item in value]
    if isinstance(value, dict):
        return {
            str(key): scrub_value(item, mode=mode)
            for key, item in value.items()
        }
    return value
