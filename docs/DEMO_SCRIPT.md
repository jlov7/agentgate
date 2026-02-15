# AgentGate 60-Second Demo Script

## Goal
Show containment in action: policy enforcement, approvals, kill switch, and evidence.

## Prep (one time)
- `make setup`
- `make try`
- `make showcase-video` (optional: record polished MP4 + teaser GIF)

## Live Script (60 seconds)
1) "AgentGate sits between the agent runtime and tools. Every call is evaluated in real time."
2) Run `make try` (or `python -m agentgate --showcase` with the stack running).
3) "This run generated a full evidence pack and metrics snapshot."
4) Open `docs/showcase/evidence.html` and scroll to the decision timeline.
5) Open `docs/showcase/metrics.prom` and point to kill switch and policy counters.

## If You Have 2 Minutes
- Show `docs/showcase/showcase.log` for the narrated run.
- Point to `docs/showcase/summary.json` for the structured results.
- Download `docs/showcase/proof-bundle-*.zip` as your handoff artifact.
- Use `make showcase-record` to capture a fresh terminal log.

## Troubleshooting
- If the showcase cannot connect, run `make dev` first.
- If OPA or Redis is down, run `docker-compose up -d`.
