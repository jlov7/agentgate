.PHONY: setup dev test lint test-adversarial demo

setup:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

dev:
	docker-compose up -d
	.venv/bin/uvicorn agentgate.main:app --reload

test:
	.venv/bin/pytest tests/ -v

test-adversarial:
	.venv/bin/python run_adversarial.py

lint:
	.venv/bin/ruff check src/
	.venv/bin/mypy src/

demo:
	bash demo/run_demo.sh
