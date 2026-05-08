# AgentGate Product Contract

## Register

product

## Product Purpose

AgentGate is a containment-first control plane for AI agent tool calls. It sits at the tool boundary, decides whether a call is allowed, denied, or requires approval, and produces evidence that security, platform, and audit teams can trust.

## Primary Users

- Security leads who need policy enforcement, containment, replay, and defensible evidence.
- Platform engineers who need rollout safety, operational telemetry, and stable integration contracts.
- Compliance reviewers who need signed exports, retention posture, and reproducible support bundles.
- Executive sponsors who need a fast proof that agent autonomy can be governed without pausing adoption.

## Product Principles

- Stop unsafe work before it executes. Observation without control is not enough.
- Every operational claim must be backed by command evidence, trace data, or signed artifacts.
- The product surface should feel like a control room: calm, dense, precise, and hard to misuse.
- Show the path from trial to production. Avoid pages that explain without letting the user act.
- Keep demo mode honest. Demo data must be labeled, deterministic, and structurally identical to production contracts.

## Anti-References

- Generic AI SaaS landing pages with purple gradients, decorative cards, and vague automation copy.
- Dashboards that bury incidents and approvals behind marketing-style sections.
- Docs-first products where users must read through pages to understand operational state.
- Security tools that report risk without giving the operator the next safe action.

## Success Criteria

- A first-time evaluator can understand the containment model and open a working console in under one minute.
- A security operator can identify active risk, inspect a session, and export evidence without reading docs.
- A policy owner can compare, review, publish, and roll back policy changes with visible blast-radius proof.
- Release readiness remains governed by `scripts/doctor.sh` and every frontend route has browser evidence.
