# Project Makefile for Agent_Project_Backend

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn
GUNICORN ?= gunicorn
REQS ?= requirements.txt
ENV_FILE ?= .env
PORT ?= 8000

.PHONY: help install run dev prod lint clean env-check

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  install     Install Python dependencies from $(REQS)"
	@echo "  env-check   Verify required environment file exists"
	@echo "  run         Start the FastAPI app on port $(PORT)"
	@echo "  dev         Start the FastAPI app in reload mode on port $(PORT)"
	@echo "  lint        Check formatting with Black and lint with Ruff"
	@echo "  clean       Remove Python cache files"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQS)

env-check:
	@$(PYTHON) -c "import os, sys; f='$(ENV_FILE)'; if not os.path.isfile(f): print(f'Missing {f}. Copy .env.example to {f} and fill in secrets.'); sys.exit(1); print(f'Found {f}.')"

run: env-check
	$(PYTHON) app.py

dev: env-check
	$(PYTHON) -m $(UVICORN) app:app --host 0.0.0.0 --port $(PORT) --reload

prod: env-check
	$(GUNICORN) -w 1 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$(PORT)

lint:
	$(PYTHON) -m black --check .
	$(PYTHON) -m ruff check .

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(path) for path in Path('.').rglob('__pycache__')]; [path.unlink() for path in Path('.').rglob('*.pyc')]"
