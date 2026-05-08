#!/usr/bin/env python3
"""Run deterministic durability drills for trace storage."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from agentgate.traces import TraceStore


def _integrity_check(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"


def _migration_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
    return int(row[0]) if row else 0


def _rollback_rehearsal(db_path: Path) -> bool:
    with sqlite3.connect(db_path) as conn:
        conn.execute("BEGIN")
        conn.execute("CREATE TABLE IF NOT EXISTS durability_drill_probe (value TEXT)")
        conn.execute("ROLLBACK")
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='durability_drill_probe'"
        ).fetchone()
    return row is None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-db", type=Path, default=Path("traces.db"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/durability-drill.json"),
    )
    args = parser.parse_args()

    trace_db = args.trace_db
    if not trace_db.exists():
        store = TraceStore(str(trace_db))
        store.close()

    backup_dir = Path("artifacts/durability")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"trace-backup-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.db"
    restore_path = backup_dir / f"trace-restore-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.db"

    shutil.copy2(trace_db, backup_path)
    shutil.copy2(backup_path, restore_path)

    source_integrity = _integrity_check(trace_db)
    restored_integrity = _integrity_check(restore_path)
    source_migrations = _migration_count(trace_db)
    restored_migrations = _migration_count(restore_path)
    rollback_ok = _rollback_rehearsal(restore_path)

    checks = {
        "source_integrity_ok": source_integrity == "ok",
        "restored_integrity_ok": restored_integrity == "ok",
        "migration_count_match": source_migrations == restored_migrations,
        "rollback_rehearsal_ok": rollback_ok,
    }

    overall = "pass" if all(checks.values()) else "fail"

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_status": overall,
        "trace_db": str(trace_db),
        "backup_path": str(backup_path),
        "restore_path": str(restore_path),
        "source_integrity": source_integrity,
        "restored_integrity": restored_integrity,
        "source_migrations": source_migrations,
        "restored_migrations": restored_migrations,
        "checks": checks,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"durability drill: {overall}")
    print(f"artifact: {args.output}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
