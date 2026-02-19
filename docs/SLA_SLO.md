# SLA and SLO

This document defines baseline service commitments for AgentGate pre-release operations.

## SLA Targets

- Monthly API availability: `99.9%`
- Monthly policy-evaluation success rate: `99.95%`
- Incident acknowledgment:
  - Sev-1: `15 minutes`
  - Sev-2: `1 hour`

## SLO Targets

- P95 policy decision latency: `<= 250ms`
- P95 tool-call end-to-end latency: `<= 2500ms`
- Error budget: `0.1%` monthly availability budget
- Replay/rollout control artifact generation success: `>= 99.5%`

## Measurement Source

- Availability and latency: Prometheus + load-test validation artifacts
- Incident timing: incident timeline records
- Evidence/control artifacts: doctor and support-bundle outputs

## Breach Policy

If an SLO breaches for two consecutive windows, trigger rollout freeze and corrective action review before the next release gate.
