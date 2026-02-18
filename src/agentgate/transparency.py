"""Merkle-style transparency helpers for evidence verification."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from agentgate.models import TraceEvent
from agentgate.traces import TraceStore


def hash_leaf(value: str) -> str:
    """Hash a leaf payload with SHA-256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_merkle_root(leaf_hashes: list[str]) -> str:
    """Build deterministic Merkle root using duplicate-last for odd levels."""
    if not leaf_hashes:
        return hash_leaf("")
    level = list(leaf_hashes)
    while len(level) > 1:
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(hash_leaf(f"{left}{right}"))
        level = next_level
    return level[0]


def build_inclusion_proof(leaf_hashes: list[str], index: int) -> list[str]:
    """Build inclusion proof for one leaf index."""
    if index < 0 or index >= len(leaf_hashes):
        raise IndexError("leaf index out of range")
    proof: list[str] = []
    level = list(leaf_hashes)
    current = index
    while len(level) > 1:
        sibling_idx = current + 1 if current % 2 == 0 else current - 1
        sibling = level[sibling_idx] if sibling_idx < len(level) else level[current]
        proof.append(sibling)
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(hash_leaf(f"{left}{right}"))
        current //= 2
        level = next_level
    return proof


def verify_inclusion_proof(
    *,
    leaf_hash: str,
    index: int,
    total_leaves: int,
    proof: list[str],
    root_hash: str,
) -> bool:
    """Verify inclusion proof against root hash."""
    if total_leaves <= 0 or index < 0 or index >= total_leaves:
        return False
    current = leaf_hash
    position = index
    for sibling in proof:
        if position % 2 == 0:
            current = hash_leaf(f"{current}{sibling}")
        else:
            current = hash_leaf(f"{sibling}{current}")
        position //= 2
    return current == root_hash


class TransparencyLog:
    """Compute per-session transparency proofs from append-only traces."""

    def __init__(self, *, trace_store: TraceStore) -> None:
        self.trace_store = trace_store

    def build_session_report(
        self, session_id: str, *, anchor: bool = False
    ) -> dict[str, object]:
        traces = self.trace_store.query(session_id=session_id)
        leaf_hashes = [hash_leaf(_canonicalize_trace(trace)) for trace in traces]
        root_hash = build_merkle_root(leaf_hashes)
        proofs: list[dict[str, object]] = []
        for idx, trace in enumerate(traces):
            proof = build_inclusion_proof(leaf_hashes, idx) if leaf_hashes else []
            leaf_hash = leaf_hashes[idx] if leaf_hashes else hash_leaf("")
            proofs.append(
                {
                    "event_id": trace.event_id,
                    "index": idx,
                    "leaf_hash": leaf_hash,
                    "proof": proof,
                    "verified": verify_inclusion_proof(
                        leaf_hash=leaf_hash,
                        index=idx,
                        total_leaves=len(leaf_hashes),
                        proof=proof,
                        root_hash=root_hash,
                    )
                    if leaf_hashes
                    else True,
                }
            )
        if anchor:
            anchor_source = os.getenv("AGENTGATE_TRANSPARENCY_ANCHOR_SOURCE", "local-ledger")
            receipt, status = _anchor_checkpoint_receipt(
                session_id=session_id,
                root_hash=root_hash,
                event_count=len(traces),
                anchor_source=anchor_source,
            )
            self.trace_store.save_transparency_checkpoint(
                session_id=session_id,
                root_hash=root_hash,
                anchor_source=anchor_source,
                status=status,
                receipt=receipt,
            )
        checkpoints = self.trace_store.list_transparency_checkpoints(session_id)
        return {
            "session_id": session_id,
            "event_count": len(traces),
            "root_hash": root_hash,
            "proofs": proofs,
            "checkpoints": checkpoints,
        }


def _canonicalize_trace(trace: TraceEvent) -> str:
    event_id = trace.event_id
    timestamp = trace.timestamp.isoformat()
    tool_name = trace.tool_name
    arguments_hash = trace.arguments_hash
    policy_decision = trace.policy_decision
    return (
        f"{event_id}|{timestamp}|{tool_name}|{arguments_hash}|{policy_decision}"
    )


def _anchor_checkpoint_receipt(
    *,
    session_id: str,
    root_hash: str,
    event_count: int,
    anchor_source: str,
) -> tuple[dict[str, Any], str]:
    payload = {
        "session_id": session_id,
        "root_hash": root_hash,
        "event_count": event_count,
        "anchored_at": datetime.now(UTC).isoformat(),
        "anchor_source": anchor_source,
    }
    url = os.getenv("AGENTGATE_TRANSPARENCY_ANCHOR_URL")
    if not url:
        return {
            "mode": "local",
            "status": "anchored",
            "payload": payload,
        }, "anchored"
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        return {
            "mode": "external",
            "status": "failed",
            "url": url,
            "payload": payload,
            "error": "unsupported anchor URL scheme",
        }, "failed"

    request_body = json.dumps(payload, sort_keys=True).encode("utf-8")
    request = Request(  # noqa: S310
        url=url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout_seconds = float(os.getenv("AGENTGATE_TRANSPARENCY_ANCHOR_TIMEOUT", "2.0"))
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310  # nosec B310
            response_body = response.read().decode("utf-8")
            parsed: dict[str, Any] | str
            try:
                parsed = json.loads(response_body)
            except json.JSONDecodeError:
                parsed = response_body
            return {
                "mode": "external",
                "status": "anchored",
                "url": url,
                "http_status": response.status,
                "payload": payload,
                "response": parsed,
            }, "anchored"
    except (HTTPError, URLError, OSError, ValueError) as exc:
        return {
            "mode": "external",
            "status": "failed",
            "url": url,
            "payload": payload,
            "error": str(exc),
        }, "failed"
