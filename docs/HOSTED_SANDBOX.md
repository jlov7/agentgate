# Hosted Browser Sandbox

Use this no-local-install sandbox to run core AgentGate flows directly from a browser against a hosted endpoint.

## How to use

1. Set **Base URL** to your hosted AgentGate API endpoint.
2. Optionally set **Tenant ID** and **Admin API Key** if your deployment requires them.
3. Run individual seeded flows or execute all flows in sequence.
4. Download the transcript JSON to share evidence of the trial session.

<div id="ag-hosted-sandbox" class="ag-lab" data-flows="../lab/sandbox/flows.json"></div>

## Notes

- The sandbox is browser-side only; no local setup is required.
- Your deployment must allow browser CORS requests for this page origin.
- Seeded flows mirror the same allow/deny patterns used in the staging reset workflow.
