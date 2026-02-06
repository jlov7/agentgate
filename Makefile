.PHONY: setup lock dev test lint test-adversarial demo showcase showcase-record showcase-video showcase-video-silent clean sbom docker docker-prod pre-commit install-hooks unit integration evals ai-evals e2e mutate load-smoke load-test load-test-remote staging-smoke check-docker verify verify-strict

# ============================================================================
# Development
# ============================================================================

setup:
	scripts/install_python_deps.sh .venv requirements/dev.lock
	@echo "\n✓ Setup complete. Run 'make dev' to start the server."

PYTHON_LOCK_BIN ?= python3.12

lock:
	@command -v $(PYTHON_LOCK_BIN) >/dev/null || { echo "$(PYTHON_LOCK_BIN) is required to refresh requirements/dev.lock"; exit 1; }
	@tmp_dir="$$(mktemp -d)"; \
		"$(PYTHON_LOCK_BIN)" -m venv "$$tmp_dir/venv"; \
		"$$tmp_dir/venv/bin/pip" install --upgrade "pip<26" pip-tools >/dev/null; \
		"$$tmp_dir/venv/bin/pip-compile" --strip-extras --extra dev --extra pdf --output-file requirements/dev.lock pyproject.toml; \
		rm -rf "$$tmp_dir"
	@echo "\n✓ Refreshed lockfile: requirements/dev.lock"

dev:
	docker-compose up -d
	.venv/bin/uvicorn agentgate.main:app --reload --host 0.0.0.0 --port 8000

run:
	.venv/bin/python -m agentgate

demo:
	bash demo/run_demo.sh

demo-interactive:
	.venv/bin/python -m agentgate --demo

showcase:
	bash demo/run_showcase.sh

showcase-record:
	bash demo/record_demo.sh docs/showcase/showcase.log demo/run_showcase.sh

showcase-video:
	bash demo/record_screen_demo.sh

showcase-video-silent:
	VOICEOVER=0 bash demo/record_screen_demo.sh

# ============================================================================
# Testing
# ============================================================================

test:
	.venv/bin/pytest tests/ -v

unit:
	.venv/bin/pytest tests/ -v -m "not integration and not evals" --cov=src/agentgate --cov-report=term --cov-report=xml

integration:
	.venv/bin/pytest tests/integration -v -m integration

evals:
	.venv/bin/pytest tests/evals -v -m evals

ai-evals:
	.venv/bin/python evals/run_evals.py

e2e:
	npx playwright test

mutate:
	.venv/bin/mutmut run
	.venv/bin/python scripts/check_mutmut.py

LOAD_SMOKE_URL ?= http://127.0.0.1:8000/health
LOAD_SMOKE_TOTAL ?= 200
LOAD_SMOKE_CONCURRENCY ?= 20
LOAD_SMOKE_TIMEOUT ?= 5

load-smoke:
	.venv/bin/python scripts/load_smoke.py --url $(LOAD_SMOKE_URL) --total $(LOAD_SMOKE_TOTAL) --concurrency $(LOAD_SMOKE_CONCURRENCY) --timeout $(LOAD_SMOKE_TIMEOUT)

LOAD_TEST_URL ?= http://127.0.0.1:8000
LOAD_TEST_VUS ?= 20
LOAD_TEST_DURATION ?= 30s
LOAD_TEST_RAMP_UP ?= 10s
LOAD_TEST_RAMP_DOWN ?= 10s
LOAD_TEST_P95 ?= 2500
LOAD_TEST_SUMMARY ?=

load-test:
	LOAD_TEST_URL=$(LOAD_TEST_URL) LOAD_VUS=$(LOAD_TEST_VUS) LOAD_DURATION=$(LOAD_TEST_DURATION) LOAD_RAMP_UP=$(LOAD_TEST_RAMP_UP) LOAD_RAMP_DOWN=$(LOAD_TEST_RAMP_DOWN) LOAD_P95=$(LOAD_TEST_P95) LOAD_TEST_SUMMARY=$(LOAD_TEST_SUMMARY) scripts/load_server.sh scripts/run_load_test.sh

load-test-remote:
	LOAD_TEST_URL=$(LOAD_TEST_URL) LOAD_VUS=$(LOAD_TEST_VUS) LOAD_DURATION=$(LOAD_TEST_DURATION) LOAD_RAMP_UP=$(LOAD_TEST_RAMP_UP) LOAD_RAMP_DOWN=$(LOAD_TEST_RAMP_DOWN) LOAD_P95=$(LOAD_TEST_P95) LOAD_TEST_SUMMARY=$(LOAD_TEST_SUMMARY) scripts/run_load_test.sh

staging-smoke:
	STAGING_URL=$(STAGING_URL) scripts/staging_smoke.sh

test-adversarial:
	.venv/bin/python run_adversarial.py

test-all: test test-adversarial

coverage:
	.venv/bin/pytest tests/ -v --cov=src/agentgate --cov-report=html --cov-report=term
	@echo "\n✓ Coverage report: htmlcov/index.html"

verify:
	.venv/bin/ruff check src/ tests/
	.venv/bin/mypy src/
	.venv/bin/pytest tests/ -v -m "not integration and not evals" --cov=src/agentgate --cov-report=term --cov-report=xml
	$(MAKE) check-docker
	.venv/bin/pytest tests/integration -v -m integration
	.venv/bin/pytest tests/evals -v -m evals
	.venv/bin/python evals/run_evals.py
	npx playwright test

check-docker:
	scripts/check_docker.sh

verify-strict: verify mutate

# ============================================================================
# Code Quality
# ============================================================================

lint:
	.venv/bin/ruff check src/
	.venv/bin/mypy src/

format:
	.venv/bin/ruff format src/ tests/
	.venv/bin/ruff check --fix src/ tests/

install-hooks:
	.venv/bin/pip install pre-commit
	.venv/bin/pre-commit install
	@echo "\n✓ Pre-commit hooks installed."

pre-commit:
	.venv/bin/pre-commit run --all-files

# ============================================================================
# Security & Compliance
# ============================================================================

sbom:
	@mkdir -p reports
	.venv/bin/pip install pip-audit cyclonedx-bom 2>/dev/null || true
	.venv/bin/pip-audit --format=cyclonedx-json --output=reports/sbom.json 2>/dev/null || \
		.venv/bin/cyclonedx-py environment -o reports/sbom.json
	@echo "\n✓ SBOM generated: reports/sbom.json"

audit:
	.venv/bin/pip install pip-audit 2>/dev/null || true
	.venv/bin/pip-audit
	@echo "\n✓ Security audit complete."

# ============================================================================
# Docker
# ============================================================================

docker:
	docker build -t agentgate:latest .
	@echo "\n✓ Docker image built: agentgate:latest"

docker-prod:
	docker-compose -f docker-compose.prod.yml build
	@echo "\n✓ Production images built."

docker-up:
	docker-compose up -d

docker-up-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "\n✓ Production stack started."

docker-down:
	docker-compose down

docker-down-prod:
	docker-compose -f docker-compose.prod.yml down

docker-logs:
	docker-compose logs -f

# ============================================================================
# Cleanup
# ============================================================================

clean:
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf *.egg-info/
	rm -rf reports/
	rm -f *.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "\n✓ Cleaned."

# ============================================================================
# Help
# ============================================================================

help:
	@echo "AgentGate Makefile"
	@echo ""
	@echo "Development:"
	@echo "  make setup           Create venv and install dependencies"
	@echo "  make lock            Refresh requirements/dev.lock using Python 3.12"
	@echo "  make dev             Start dev server with hot reload"
	@echo "  make run             Start server without reload"
	@echo "  make demo            Run scripted demo"
	@echo "  make demo-interactive Run interactive demo"
	@echo "  make showcase        Run showcase demo + generate artifacts"
	@echo "  make showcase-record Record showcase output to docs/showcase/showcase.log"
	@echo "  make showcase-video  Record a polished MP4 (voiceover + teaser GIF)"
	@echo "  make showcase-video-silent Record MP4 without voiceover"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run unit tests"
	@echo "  make unit            Run unit tests with coverage"
	@echo "  make integration     Run integration tests"
	@echo "  make evals           Run golden-set eval tests"
	@echo "  make ai-evals        Run evaluation harness (golden cases + invariants)"
	@echo "  make e2e             Run Playwright E2E tests"
	@echo "  make mutate          Run mutation tests for critical modules"
	@echo "  make test-adversarial Run security tests"
	@echo "  make load-smoke      Run a lightweight load smoke test (requires a running server)"
	@echo "  make load-test       Run a k6 load test (starts local server)"
	@echo "  make load-test-remote Run a k6 load test against LOAD_TEST_URL"
	@echo "  make staging-smoke   Run smoke + load against STAGING_URL"
	@echo "  make check-docker    Fail fast when Docker daemon is unavailable"
	@echo "  make test-all        Run all tests"
	@echo "  make coverage        Run tests with coverage"
	@echo "  make verify          Run lint, typecheck, unit, integration, evals, AI evals, and E2E tests"
	@echo "  make verify-strict   Run verify plus mutation testing (nightly)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            Run linter and type checker"
	@echo "  make format          Auto-format code"
	@echo "  make install-hooks   Install pre-commit hooks"
	@echo "  make pre-commit      Run pre-commit on all files"
	@echo ""
	@echo "Security:"
	@echo "  make sbom            Generate SBOM (CycloneDX)"
	@echo "  make audit           Run security audit"
	@echo ""
	@echo "Docker:"
	@echo "  make docker          Build Docker image"
	@echo "  make docker-prod     Build production images"
	@echo "  make docker-up       Start dev containers"
	@echo "  make docker-up-prod  Start production stack"
	@echo "  make docker-down     Stop containers"
	@echo ""
	@echo "Other:"
	@echo "  make clean           Remove build artifacts"
	@echo "  make help            Show this help"
