# Changelog

All notable changes to AgentGate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- k6-based load testing harness plus `make load-test`/`make load-test-remote` targets.
- Staging smoke + load runner (`make staging-smoke`) and a scheduled CI load-test job.

### Fixed

- Made Playwright and load-test helper servers use dedicated configurable ports by default to avoid false gate failures when local `:8000` is occupied.
- Fixed `scripts/staging_smoke.sh` empty optional-args handling under `set -u` and added regression coverage.

## [0.2.1] - 2026-01-23

### Fixed

- Align sample evidence generator and version references with v0.2.1

## [0.2.0] - 2026-01-22

### Added

- **Prometheus Metrics** — Full observability at `/metrics` endpoint with counters, gauges, and histograms for tool calls, latencies, kill switch activations, and health status
- **Webhook Notifications** — Real-time alerts for critical events (kill switch activation, policy denials, rate limits, health changes) with HMAC signing
- **PDF Evidence Export** — Audit-ready PDF reports via WeasyPrint (optional dependency)
- **Cryptographic Signing** — HMAC-SHA256 signatures on evidence packs when `AGENTGATE_SIGNING_KEY` is set
- **Rate Limit Headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on tool call responses
- **Policy Hot-Reload** — `POST /admin/policies/reload` to update policies without restart
- **Interactive CLI** — `python -m agentgate --demo` for interactive demonstration
- **Production Docker** — Hardened `docker-compose.prod.yml` with security best practices
- **SBOM Generation** — CycloneDX bill of materials via `make sbom`
- **Pre-commit Hooks** — Code quality enforcement with Ruff, MyPy, Bandit
- **OpenAPI Documentation** — Interactive docs at `/docs` and `/redoc`
- **ASCII Banner** — Startup banner for visual identity
- **Redis Connection Pooling** — Improved performance under load
- **Security Scanning** — pip-audit and Bandit integration in CI

### Changed

- Version bump from 0.1.0 to 0.2.0
- Enhanced `RateLimiter` with `RateLimitStatus` dataclass for detailed status info
- Expanded test coverage configuration
- Improved error handling with structured `ErrorResponse` model
- Updated CI workflow with parallel jobs for lint, test, security, and SBOM

### Security

- Added `ErrorCode` constants for consistent error classification
- Evidence packs now include hash algorithm metadata
- Webhook payloads are HMAC-signed when secret is configured
- Docker production profile enforces least-privilege principles

## [0.1.0] - 2026-01-21

### Added

- Initial release
- Policy gates with OPA/Rego integration
- Kill switches (session, tool, global)
- Credential broker stub
- Evidence export (JSON, HTML)
- Append-only trace store (SQLite)
- Rate limiting with sliding window
- 31 automated tests (14 unit, 17 adversarial)
- FastAPI HTTP API
- Docker Compose development setup
- CI/CD with GitHub Actions
