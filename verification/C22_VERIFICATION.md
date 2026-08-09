# C22 Verification

Verification date: 2026-08-09

Status: PASS

## Automated results

```text
.venv/bin/pytest packages/intelligence/tests/ -q -rs
496 passed, 0 skipped

PYTHONPATH=apps/backend:packages/intelligence/src:simulator \
  .venv/bin/pytest apps/backend/tests/ -q -rs
38 passed, 0 skipped

.venv/bin/pytest simulator/tests/ -q -rs
15 passed, 0 skipped

npm run lint && npm run typecheck && npm run build
PASS; production bundle emitted (size notice only)

Alembic upgrade head / downgrade base
PASS through c21outcomes
```

## Real HTTP CLI run

Temporary local Uvicorn/SQLite backend on `127.0.0.1:8766` followed by:

```text
PYTHONPATH=. .venv/bin/python -m simulator.lossline_simulator.runner \
  --scenario predictive --api-url http://127.0.0.1:8766 --seed 42
```

Observed: all eight event requests returned 202; review returned 200; Predictive Today and three evaluation queries returned 200. Final summary:

```text
{"decision_status":"MANAGER_APPROVED","evaluation_count":9,"forecast_count":3,"outcome_count":3}
```

## Gate

| Requirement | Result |
|---|---|
| Simulator uses only `POST /events` for data | PASS |
| Redis copies bypass the reactive detector and are acknowledged | PASS |
| Schedule contains no forecasts/target actuals | PASS |
| Six comparable history windows | PASS |
| Three backend forecasts | PASS |
| Inventory/capacity/risk/driver/dossier chain | PASS |
| Strict submission and deterministic guard | PASS |
| Durable manager review and approval | PASS |
| Three matured actual outcomes | PASS |
| Forecast/risk/decision evaluations | 9 — PASS |
| Identical seed reproduces artifact IDs | PASS |
| Real HTTP simulator CLI | PASS |
| UI/build and all regressions | PASS |

## Environment limitation

`docker` was not installed on this verification host (`command not found`), so Compose was not executed. The runbook and manifests are retained; this report makes no container-runtime claim.
