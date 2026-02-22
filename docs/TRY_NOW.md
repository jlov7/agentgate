# Try AgentGate in 5 Minutes

<div data-ag-context></div>

## Quick Start Summary

Run one command to generate signed evidence artifacts and a proof bundle, then continue to hosted and operational journeys.

## One command

```bash
make try
```

What `make try` does:

1. Verifies Docker is available.
2. Starts Redis + OPA and a local AgentGate server.
3. Runs the full showcase flow with signed evidence output.
4. Builds a downloadable proof bundle zip in `docs/showcase/`.
5. Prints clickable local artifact paths.

## What to open first

1. `docs/showcase/evidence.html`
2. `docs/showcase/metrics.prom`
3. `docs/showcase/showcase.log`
4. `docs/showcase/proof-bundle-*.zip`

## Optional: reuse an existing showcase summary

```bash
.venv/bin/python scripts/try_now.py --summary-path docs/showcase/summary.json --output-dir docs/showcase
```

## If something fails

- Run `make setup` if `.venv` is missing.
- Start Docker Desktop and retry.
- Check `docs/showcase/summary.json` and `docs/showcase/showcase.log` for the failure reason.

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="../HOSTED_SANDBOX/">Run live API flows in hosted sandbox</a></li>
    <li><a href="../DEMO_LAB/">Walk through scenario narratives and blast radius</a></li>
    <li><a href="../JOURNEYS/">Move to role-based production journeys</a></li>
  </ol>
</div>
