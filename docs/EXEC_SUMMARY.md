# AgentGate Executive Summary

## Positioning
AgentGate is a containment-first security gateway for AI agents. It sits between agent runtimes and tools, enforces policy on every call, and produces audit-grade evidence automatically.

## Why Now
- Agents are moving from copilots to autonomous systems with write access.
- Most platforms can observe behavior but cannot block it in real time.
- Compliance teams need evidence, not screenshots and log fragments.

## What It Delivers
- Real-time enforcement: allow, deny, or require approval on every tool call.
- Kill switches at session, tool, and global levels.
- Evidence packs with cryptographic integrity.
- Prometheus metrics and webhook alerts for live ops.

## Differentiators
| Capability | Typical Platforms | AgentGate |
| --- | --- | --- |
| Stop a misbehaving agent in real time | Limited | Yes (kill switch) |
| Enforce policy at the tool boundary | Partial | Yes (OPA/Rego) |
| Generate audit-grade evidence | Partial | Yes (JSON/HTML/PDF) |
| Provide containment proof | No | Yes (trace + signature) |

## Proof in 60 Seconds
1) Run `make try` to start the local stack, execute the demo, and generate evidence.
2) Open `docs/showcase/evidence.html` for the audit pack.
3) Open `docs/showcase/metrics.prom` for live controls in Prometheus format.

## Decision Ask
Use AgentGate as the reference implementation for containment-first AI governance and as the baseline for production hardening.
