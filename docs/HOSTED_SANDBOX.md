# Hosted Browser Sandbox

<div data-ag-context></div>

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

## Move from Sandbox to Production

1. Replace sample tenant IDs with production tenant identifiers.
2. Move from trial API key to role-scoped production credentials.
3. Lock requested API version to your deployment target.
4. Run replay + rollout checks before enabling write actions.
5. Capture transcript and attach it to your rollout approval.

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="TRY_NOW/">Generate local proof bundle artifacts</a></li>
    <li><a href="DEMO_LAB/">Replay flagship risk scenarios</a></li>
    <li><a href="JOURNEYS/">Move into role-based journeys</a></li>
  </ol>
</div>
