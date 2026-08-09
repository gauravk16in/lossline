# C22 — Integrated Seeded Predictive Demo

Status: complete

## Purpose

Prove the predictive architecture as one repeatable public-API run from causal synthetic inputs through matured evaluation, without simulator-generated forecasts or direct database/Redis writes.

## Golden flow

Scenario `predictive_stockout_v1`, seed 42:

1. The simulator generates six causally coherent comparable history windows.
2. It posts those six actual windows through `POST /events`.
3. It posts one future scheduled window containing only context, inventory, capacity, SKU static inputs and timing—no forecasts or target actuals.
4. The backend constructs C04 snapshots, selects the explicit C05 baseline fallback, creates three SKU forecasts, C08 inventory projections, one C09 shared-capacity projection, risks, C10 drivers and a C11 dossier.
5. C13 strict submission, C14 guard, C16 durable review checkpoint and C17 deterministic grounded explanation execute. The manager review API approves the guarded candidate.
6. The simulator posts the later actual window through `POST /events`.
7. C21 persists three matured outcomes and nine forecast/risk/decision evaluation records.
8. Predictive Today returns forecast-versus-actual, projections, evidence and decision status.

The schedule event is tested to contain none of `forecast_id`, point/lower/upper demand, actual demand, fulfilled quantity or unfulfilled quantity. Model outputs belong exclusively to backend code.

## Reproducibility

Two reset runs with identical seed/window produce identical forecast, dossier, decision, trace and outcome IDs. Different seeds remain supported by the causal generator. Event count for the golden run is exactly eight: six history, one schedule and one actual.

## Verification

- In-process public HTTP/ASGI end-to-end tests exercise real FastAPI dependencies and persistence.
- A real Uvicorn process plus simulator CLI completed successfully with 3 forecasts, manager approval, 3 outcomes and 9 evaluations.
- Predictive outbox copies are acknowledged by the Redis consumer without entering the reactive detector pipeline; a routing regression test enforces this coexistence boundary.
- Intelligence, backend and simulator suites pass with zero skips.
- React lint/typecheck/build pass.
- Alembic upgrades and downgrades through C21 pass.
- `docker-compose.yml` and all Dockerfiles remain present, but Docker itself was unavailable on the verification host; no container-runtime claim is made.

## Definition of done

C22 is complete when all simulator inputs/actuals traverse `POST /events`, the full C04–C21 artifact chain is observable, approval gates actual evaluation, identical runs reproduce IDs, real HTTP CLI and automated E2E tests pass, all component regressions/builds pass, claims are limited to collected evidence, and the runbook describes both reactive and predictive demos.
