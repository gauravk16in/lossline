.PHONY: setup dev test lint db-migrate db-revision

VENV = app/backend/.venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip
ALEMBIC = $(VENV)/Scripts/alembic

setup:
	python -m venv $(VENV)
	$(PIP) install -r app/backend/requirements.txt

dev:
	cd app/backend && ../../$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd app/backend && ../../$(PYTHON) -m pytest

lint:
	$(VENV)/Scripts/black --check app/backend/app
	$(VENV)/Scripts/flake8 app/backend/app
	$(VENV)/Scripts/mypy app/backend/app

db-migrate:
	cd app/backend && ../../$(ALEMBIC) upgrade head

# Allow passing arguments to db-revision like: make db-revision init_schema
db-revision:
	cd app/backend && ../../$(ALEMBIC) revision --autogenerate -m "schema update"
