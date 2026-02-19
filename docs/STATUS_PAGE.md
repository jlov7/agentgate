# Status Page

Use the static status page template at `docs/status/index.html` as the default public trust surface.

## What To Publish

- Overall platform status (`Operational`, `Degraded`, `Major Incident`)
- Component-level health
- SLO snapshot (availability/latency/error budget)
- Current incident summary and next update time
- Links to support tiers and incident communication channel

## Local Preview

Open `docs/status/index.html` directly in a browser, or publish via docs hosting as a static page.

## Update Rule

Any production-impacting incident should update the status page within the first response window defined in `docs/SUPPORT_TIERS.md`.
