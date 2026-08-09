# LOSSLine MVP demo

## Start

Requirements: Docker with Compose support. No LLM key is required; all calculations and displayed explanation fallback are deterministic.

```bash
`docker compose up --build -d postgres redis backend frontend`
```

Wait for all services to become healthy, then open `http://localhost:3000`.

## Run the lunch-rush scenario

```bash
docker compose --profile demo run --rm simulator
```

The simulator resets synthetic records, submits historical and live events only through `POST /api/v1/events`, and pauses when an incident awaits approval. Approve the simulated action in the dashboard. The runner then submits recovery events and requests deterministic outcome verification. The incident should finish as `RESOLVED` with an `IMPROVED` outcome.

## Run without Docker

Use SQLite and inline processing in one terminal:

```bash
DATABASE_URL=sqlite+aiosqlite:///./lossline.sqlite3 \
INLINE_PROCESSING=true \
PYTHONPATH=apps/backend:packages/intelligence/src \
.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
```

In another terminal, run `cd apps/frontend && npm run dev`, then execute the simulator with:

```bash
PYTHONPATH=. .venv/bin/python -m simulator.lossline_simulator.runner --speed 120
```

## Verify APIs

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/incidents
curl http://localhost:8000/api/v1/analytics/summary
```

## Test locally

```bash
.venv/bin/pytest packages/intelligence/tests/
PYTHONPATH=apps/backend:packages/intelligence/src .venv/bin/pytest apps/backend/tests/
PYTHONPATH=apps/backend:simulator .venv/bin/pytest simulator/tests/
cd apps/frontend && npm ci && npm run build
```

## Reset and stop

`POST /api/v1/demo/reset` removes synthetic demo data only. To stop services:

```bash
docker compose down
```
