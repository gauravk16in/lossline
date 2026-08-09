# ADR 0019 — Additive Predictive Persistence and API

Status: accepted — 2026-08-09

## Decision

Add predictive tables and `/api/v1/predictive/*` APIs without renaming or removing the functioning reactive path. Store queryable scope plus the complete validated contract payload. Treat deterministic artifact IDs as immutable, use `outlet_id` on all new tables, and load ML only after an accepted evaluation record; otherwise select baseline explicitly.

Manager review may approve or reject an already guarded candidate with an idempotency key. It cannot submit a new unguarded action. Schedule future-window cycles by outlet timezone and named service window with deterministic daily run keys.

## Consequences

The database temporarily contains separate reactive and predictive concepts, avoiding a big-bang migration. JSON payloads preserve full contracts while indexed columns support operational reads. Later schema normalization requires a migration and parity proof.

## Verification

Alembic upgrade/downgrade runs on SQLite; backend integration tests cover every persistence/API/review/fallback/scheduler boundary and the reactive suite remains green.
