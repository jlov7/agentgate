# Testing AgentGate

This project uses pytest for automated testing and FastAPI's TestClient for API
integration checks. There is no web UI, so there are no E2E browser tests.

## Setup

```bash
make setup
```

## PDF export dependencies (WeasyPrint)

PDF integration tests require WeasyPrint and system libraries.

```bash
brew install pango libffi gdk-pixbuf
.venv/bin/pip install weasyprint
```

## Verify (full QA run)

```bash
make verify
```

`make verify` runs:

- Ruff linting on `src/` and `tests/`
- MyPy type checking on `src/`
- Unit + adversarial tests with coverage
- Integration API contract tests and a live-stack test (Redis + OPA via Docker)
- PDF export integration test using WeasyPrint
- Golden-set eval tests

## Optional commands

```bash
make lint
make unit
make integration
make evals
make coverage
```

## Local run

```bash
make dev
```

This starts Redis + OPA via Docker Compose and runs the FastAPI server on
`http://localhost:8000`.

## Docker requirement

`make verify` runs a live-stack integration test that starts Redis and OPA
containers using Docker and spins up a local Uvicorn server against them.
Make sure Docker is installed and running.
