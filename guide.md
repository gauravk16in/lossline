# LOSSLine usage and testing guide

This guide explains how to run the backend and frontend, exercise the demo, call the API, and run the test suites.

## Current application state

- Backend: FastAPI, available at `http://localhost:8000`.
- Frontend: React + Vite. Docker serves it at `http://localhost:3000`; the local Vite server normally uses `http://localhost:5173`.
- API documentation: `http://localhost:8000/docs`.
- The current frontend overview is populated from frontend mock data. It is useful for reviewing and developing the UI, but it does not yet read live backend data or submit manager decisions.
- The simulator is the easiest way to populate and exercise the backend end to end.
- An LLM API key is optional. Calculations and fallback explanations are deterministic.

## Option 1: Run the complete stack with Docker

This is the recommended way to use the project because it starts PostgreSQL, Redis, the backend, and the frontend together.

### Requirements

- Docker with Docker Compose
- Ports `3000`, `5432`, `6379`, and `8000` available

### 1. Create the root environment file

From the repository root, create `.env` with development-only credentials:

```dotenv
POSTGRES_DB=lossline
POSTGRES_USER=lossline
POSTGRES_PASSWORD=lossline_demo

DATABASE_URL=postgresql+asyncpg://lossline:lossline_demo@postgres:5432/lossline
DIRECT_DATABASE_URL=postgresql://lossline:lossline_demo@postgres:5432/lossline

INGEST_API_KEY=dev-ingest-key
MANAGER_API_KEY=dev-manager-key
ADMIN_API_KEY=dev-admin-key
```

Do not use these example keys in a public or production deployment.

### 2. Build and start the services

```bash
docker compose up --build -d postgres redis backend frontend
docker compose ps
```

Wait until `postgres`, `redis`, and `backend` report healthy. If a service fails, inspect it with:

```bash
docker compose logs backend
docker compose logs postgres
docker compose logs redis
```

The backend container applies Alembic migrations before starting.

### 3. Open and verify the application

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Backend readiness: `http://localhost:8000/ready`
- Interactive API docs: `http://localhost:8000/docs`

Quick checks:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
curl --fail http://localhost:8000/api/v1/incidents
```

### 4. Exercise the backend with the simulator

Run the operational lunch-rush scenario:

```bash
docker compose --profile demo run --rm simulator
```

Run the predictive scenario:

```bash
docker compose --profile demo run --rm simulator --scenario predictive --seed 42
```

For a successful predictive run, the final summary should include:

```text
{"decision_status":"MANAGER_APPROVED","evaluation_count":9,"forecast_count":3,"outcome_count":3}
```

Inspect the generated backend records:

```bash
curl http://localhost:8000/api/v1/incidents
curl http://localhost:8000/api/v1/analytics/summary
curl http://localhost:8000/api/v1/predictive/today/meghana_indiranagar/DINNER
curl http://localhost:8000/api/v1/predictive/analytics/summary
```

The simulator sends events through `POST /api/v1/events`; it does not write directly to PostgreSQL or Redis.

### 5. Stop the stack

```bash
docker compose down
```

The PostgreSQL data remains in the named Docker volume. To remove that data as well, use `docker compose down -v` only when you intentionally want a clean database.

## Option 2: Run locally for development

### Requirements

- Python 3.12
- Node.js compatible with the committed frontend lockfile (Node 22 is used by the Docker build)
- npm

The repository's shared Python environment is `.venv/`. If it has not been prepared:

```bash
make setup
```

### Start the backend without PostgreSQL or Redis

SQLite plus inline processing is the smallest local setup:

```bash
DATABASE_URL=sqlite+aiosqlite:///./lossline.sqlite3 \
DIRECT_DATABASE_URL=sqlite:///./lossline.sqlite3 \
INLINE_PROCESSING=true \
INGEST_API_KEY=dev-ingest-key \
MANAGER_API_KEY=dev-manager-key \
ADMIN_API_KEY=dev-admin-key \
PYTHONPATH=apps/backend:packages/intelligence/src \
.venv/bin/python -m uvicorn src.main:app \
  --app-dir apps/backend --reload --host 127.0.0.1 --port 8000
```

SQLite tables are created on backend startup in this mode. Confirm the service in another terminal:

```bash
curl --fail http://127.0.0.1:8000/ready
```

### Start the frontend

In another terminal:

```bash
cd apps/frontend
npm ci
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`. During local development, requests made to frontend paths beginning with `/api` are proxied to `http://localhost:8000`.

### Run the simulator against the local backend

The simulator needs the same role keys that were supplied to the backend:

```bash
LOSSLINE_INGEST_KEY=dev-ingest-key \
LOSSLINE_MANAGER_KEY=dev-manager-key \
LOSSLINE_ADMIN_KEY=dev-admin-key \
PYTHONPATH=. \
.venv/bin/python -m simulator.lossline_simulator.runner \
  --api-url http://127.0.0.1:8000 --speed 120
```

For the predictive scenario:

```bash
LOSSLINE_INGEST_KEY=dev-ingest-key \
LOSSLINE_MANAGER_KEY=dev-manager-key \
LOSSLINE_ADMIN_KEY=dev-admin-key \
PYTHONPATH=. \
.venv/bin/python -m simulator.lossline_simulator.runner \
  --scenario predictive --api-url http://127.0.0.1:8000 --seed 42
```

## Calling protected backend endpoints

Public read endpoints such as `/health`, `/ready`, `/api/v1/incidents`, and the analytics endpoints do not require a key. Protected endpoints use the `X-LOSSLine-Key` header and one of three roles:

- Ingest key: event ingestion.
- Manager key: operational and predictive decisions.
- Admin key: demo-run creation, completion, deletion, and reset.

Example event request:

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H 'Content-Type: application/json' \
  -H 'X-LOSSLine-Key: dev-ingest-key' \
  --data @event.json
```

Use `http://localhost:8000/docs` to inspect the exact request and response schemas. Supplying no key to a protected endpoint returns `401`; starting the backend without that role's configured key returns `503` for the endpoint.

## Run the automated tests

Run everything from the repository root:

```bash
make test
```

Run individual Python suites:

```bash
make test-intelligence
make test-backend
make test-simulator
```

Run one intelligence test while developing:

```bash
.venv/bin/pytest \
  packages/intelligence/tests/test_signal_model.py::test_signal_accepts_valid_detector_output \
  -v
```

Check the frontend:

```bash
cd apps/frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

There is currently no frontend browser-test command in `package.json`; linting, TypeScript checking, and a production build are the available frontend verification steps.

## Common problems

- `set POSTGRES_DB in .env`: the root `.env` is missing one or more Compose variables. Use the Docker example above.
- Backend cannot connect to PostgreSQL in Docker: the database host in both database URLs must be `postgres`, not `localhost`.
- Protected endpoint returns `401`: send the correct role's value in `X-LOSSLine-Key`.
- Protected endpoint returns `503`: configure that role's API key and restart the backend.
- Local simulator says a role key is missing: set all three `LOSSLINE_INGEST_KEY`, `LOSSLINE_MANAGER_KEY`, and `LOSSLINE_ADMIN_KEY` variables.
- Local backend cannot connect to Redis: use `INLINE_PROCESSING=true`, or start Redis and configure `REDIS_URL`.
- Frontend shows data that differs from the API: this is expected for now because the overview uses `src/data/overviewMockData.ts` rather than live API responses.
