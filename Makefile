# Project Makefile for Agent_Project_Backend

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
REQS ?= requirements.txt
ENV_FILE ?= .env

.PHONY: help install run dev lint clean env-check

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  install     Install Python dependencies from $(REQS)"
	@echo "  env-check   Verify required environment file exists"
	@echo "  run         Start the FastAPI app with uvicorn"
	@echo "  dev         Start the FastAPI app in reload mode"
	@echo "  lint        Check formatting and linting if tools are installed"
	@echo "  clean       Remove Python cache files"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQS)

env-check:
	@$(PYTHON) -c "import os, sys; f='$(ENV_FILE)'; if not os.path.isfile(f): print(f'Missing {f}. Copy .env.example to {f} and fill in secrets.'); sys.exit(1); print(f'Found {f}.')"

run: env-check
	$(PYTHON) app.py

dev: env-check
	$(UVICORN) app:app --host 0.0.0.0 --port 1234 --reload

lint:
	@command -v black >/dev/null 2>&1 && black . || echo "black is not installed"
	@command -v ruff >/dev/null 2>&1 && ruff check . || echo "ruff is not installed"

clean:
	@find . -type f -name '__pycache__' -prune -o -name '*.pyc' -print -delete
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
