.PHONY: setup dev test test-intelligence test-backend test-simulator frontend-dev frontend-build db-migrate db-revision

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic
PYTHONPATH := apps/backend:packages/intelligence/src

setup:
	python3.12 -m venv $(VENV)
	$(PIP) install -e "packages/intelligence[dev]"
	$(PIP) install -r apps/backend/requirements.txt
	cd apps/frontend && npm ci

dev:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m uvicorn src.main:app --app-dir apps/backend --reload --host 0.0.0.0 --port 8000

test: test-intelligence test-backend test-simulator

test-intelligence:
	$(PYTEST) packages/intelligence/tests/

test-backend:
	INLINE_PROCESSING=false PYTHONPATH=$(PYTHONPATH) $(PYTEST) apps/backend/tests/

test-simulator:
	INLINE_PROCESSING=false PYTHONPATH=$(PYTHONPATH):simulator $(PYTEST) simulator/tests/

frontend-dev:
	cd apps/frontend && npm run dev

frontend-build:
	cd apps/frontend && npm run build

db-migrate:
	cd apps/backend && ../../$(ALEMBIC) upgrade head

db-revision:
	cd apps/backend && ../../$(ALEMBIC) revision --autogenerate -m "$(MESSAGE)"
