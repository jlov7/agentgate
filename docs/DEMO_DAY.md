# Demo Day Playbook

## Goal

Deliver a demo that lands with both executives and engineers in under 10 minutes.

## Experience Ladder

1. **See it (90s)**: open `DEMO_LAB.md` and replay one scenario.
2. **Try it (5m)**: run `make try`.
3. **Trust it (15m)**: walk through evidence, blast radius, and rollback lineage.

## Suggested Agenda (10 minutes)

1. **Problem framing (60s)**
   Explain the monitoring-vs-containment gap for agent tool access.
2. **Interactive replay (2m)**
   In `DEMO_LAB.md`, run policy drift and quarantine scenarios.
3. **Live run (3m)**
   Run `make try` and open generated `evidence.html` + `metrics.prom`.
4. **Governance proof (2m)**
   Show `proof-bundle-*.zip` and explain signed evidence + incident lineage.
5. **Technical deep dive (2m)**
   Cover deterministic replay, exactly-once quarantine orchestration, and tenant canary rollback gates.

## Talk Tracks

### Non-technical

- AgentGate is a safety checkpoint between agents and tools.
- It can stop risky behavior in real time.
- It automatically generates evidence suitable for audits and compliance reviews.

### Technical

- Every tool call is policy-evaluated and trace-persisted.
- Replay engine computes policy deltas and blast radius before rollout.
- Quarantine pipeline coordinates kill + revocation exactly once.
- Tenant rollouts are signature-verified and canary-gated with automatic rollback.

## Artifact handoff checklist

1. Send `proof-bundle-*.zip`.
2. Send link to `DEMO_LAB.md`.
3. Send link to `TRY_NOW.md`.
4. Include one-sentence outcome per scenario.
