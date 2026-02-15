"""Merkle-style transparency helpers for evidence verification."""

from __future__ import annotations

import hashlib

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

    def build_session_report(self, session_id: str) -> dict[str, object]:
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
        return {
            "session_id": session_id,
            "event_count": len(traces),
            "root_hash": root_hash,
            "proofs": proofs,
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
