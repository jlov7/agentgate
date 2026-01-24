# Threat Model (Condensed)

## Threats and Controls
| Threat | Control | Evidence/Signal |
| --- | --- | --- |
| Policy bypass via unknown tool | Default deny + allowlist | Policy decision trace
| Unauthorized data write | REQUIRE_APPROVAL + token | Approval trace + audit event
| Lateral movement across tools | Session-scoped policy + kill switches | Kill switch events
| Replay or tampering | Append-only trace store | Integrity signature
| High-rate abuse | Rate limit headers + counters | Prometheus metrics
| Silent failure of dependencies | Health checks + alerts | /health + webhooks

## Assumptions
- OPA and Redis are reachable and monitored.
- Policies are reviewed and versioned.
- Evidence packs are exported to durable storage.

## Out of Scope
- Production hardening for multi-node clusters.
- Long-term key management for signing (recommend KMS/Vault).
- Data residency and compliance certifications.
