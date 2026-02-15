# Product Decision Log

Use this file only when release gates are blocked by product or policy decisions.

## Open Questions

None.

## Resolved Questions

1. Should release runs have access to PyPI (or a mirror/artifact cache) so `make setup` can install `annotated-doc==0.0.4` and complete the doctor gate? Without this, `scripts/doctor.sh` cannot run.
   - Resolution: Dependency access restored on 2026-02-15; `scripts/doctor.sh` and `make verify` run successfully.
