# LOSSLine MVP demo

## Start

Requirements: Docker with Compose support. No LLM key is required; all calculations and displayed explanation fallback are deterministic.

```bash
docker compose up --build -d postgres redis backend frontend
```

Wait for all services to become healthy, then open `http://localhost:3000`.

## Run the lunch-rush scenario

```bash
docker compose --profile demo run --rm simulator
```

The simulator resets synthetic records, submits historical and live events only through `POST /api/v1/events`, and pauses when an incident awaits approval. Approve the simulated action in the dashboard. The runner then submits recovery events and requests deterministic outcome verification. The incident should finish as `RESOLVED` with an `IMPROVED` outcome.

## Run the predictive scenario

```bash
docker compose --profile demo run --rm simulator --scenario predictive --seed 42
```

This runner resets synthetic records and posts six matured history windows, one
future scheduled window and one later actual window only through
`POST /api/v1/events`. The backend creates three SKU forecasts, inventory and
capacity projections, risks, drivers, a frozen dossier, a guarded decision,
manager approval, three actual outcomes and nine forecast/risk/decision
evaluations. The expected final CLI summary contains:

```text
{"decision_status":"MANAGER_APPROVED","evaluation_count":9,"forecast_count":3,"outcome_count":3}
```

Open `http://localhost:3000/predictive` to inspect Forecast versus Actual,
stockout/capacity evidence, associated drivers and review status.

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

For the predictive run:

```bash
PYTHONPATH=. .venv/bin/python -m simulator.lossline_simulator.runner \
  --scenario predictive --api-url http://127.0.0.1:8000 --seed 42
```

## Verify APIs

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/incidents
curl http://localhost:8000/api/v1/analytics/summary
curl http://localhost:8000/api/v1/predictive/today/meghana_indiranagar/DINNER
curl http://localhost:8000/api/v1/predictive/analytics/summary
```

## Test locally

```bash
.venv/bin/pytest packages/intelligence/tests/
PYTHONPATH=apps/backend:packages/intelligence/src:simulator .venv/bin/pytest apps/backend/tests/
.venv/bin/pytest simulator/tests/
cd apps/frontend && npm ci && npm run lint && npm run typecheck && npm run build
```

## Reset and stop

`POST /api/v1/demo/reset` removes synthetic demo data only. To stop services:

```bash
docker compose down
```
