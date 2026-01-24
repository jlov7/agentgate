.PHONY: setup dev test lint test-adversarial demo clean sbom docker docker-prod pre-commit install-hooks unit integration evals ai-evals e2e mutate verify verify-strict

# ============================================================================
# Development
# ============================================================================

setup:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	@echo "\n✓ Setup complete. Run 'make dev' to start the server."

dev:
	docker-compose up -d
	.venv/bin/uvicorn agentgate.main:app --reload --host 0.0.0.0 --port 8000

run:
	.venv/bin/python -m agentgate

demo:
	bash demo/run_demo.sh

demo-interactive:
	.venv/bin/python -m agentgate --demo

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
	.venv/bin/pytest tests/integration -v -m integration
	.venv/bin/pytest tests/evals -v -m evals
	.venv/bin/python evals/run_evals.py
	npx playwright test

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
	@echo "  make dev             Start dev server with hot reload"
	@echo "  make run             Start server without reload"
	@echo "  make demo            Run scripted demo"
	@echo "  make demo-interactive Run interactive demo"
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
