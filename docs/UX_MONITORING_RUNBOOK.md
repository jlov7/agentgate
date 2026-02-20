# UX Monitoring Runbook

## Signals to Watch

1. Onboarding completion rate.
2. Trial flow pass/fail ratio.
3. Drop-off between sandbox and replay journey.
4. Error-rate spikes on primary guided flows.
5. Support tickets tagged as navigation confusion.

## Response Workflow

1. Identify highest-impact friction point from telemetry/support.
2. Reproduce with persona test script.
3. Patch with smallest safe UX change.
4. Re-verify (`make verify`) and publish changelog note.

## Escalation

Escalate immediately when:

1. Users cannot reach first value.
2. Navigation dead-end blocks critical workflows.
3. UX regressions obscure safety-critical controls.
