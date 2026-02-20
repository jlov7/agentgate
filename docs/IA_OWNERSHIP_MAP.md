# IA Ownership Map

## Purpose

Define source-of-truth ownership for key UX surfaces so updates remain coherent and maintainable.

## Page Ownership Matrix

| Surface | Primary Owner | Secondary Owner | Update Trigger |
|---|---|---|---|
| `GET_STARTED.md` | Product Design | Developer Experience | New onboarding friction findings |
| `JOURNEYS.md` | Product Operations | Security Engineering | Workflow changes in replay/incidents/rollouts |
| `WORKSPACES.md` | Product Design | Support | Persona model changes |
| `HOSTED_SANDBOX.md` | Developer Experience | Platform Engineering | API contract or flow fixture changes |
| `DEMO_LAB.md` | Product Marketing | Security Engineering | Scenario or risk narrative changes |
| `REPLAY_LAB.md` | Security Engineering | Product Design | Policy replay capability changes |
| `INCIDENT_RESPONSE.md` | Security Operations | Support | Incident model/runbook changes |
| `TENANT_ROLLOUTS.md` | Platform Engineering | Security Engineering | Rollout controller/gate changes |
| `OPERATIONAL_TRUST_LAYER.md` | Compliance | Support Operations | SLA/SLO/support updates |
| `docs/javascripts/ux-shell.js` | Frontend Engineering | Product Design | Navigation/onboarding behavior changes |

## Governance Rule

1. No journey page changes without owner review.
2. Every UX-surface change must update this ownership map if responsibility shifts.
