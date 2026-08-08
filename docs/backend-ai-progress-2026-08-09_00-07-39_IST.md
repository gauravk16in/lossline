# Backend and Intelligence Progress Report

**Audit timestamp:** 2026-08-09T00:07:39+05:30 (Asia/Kolkata)  
**Repository:** LOSSLine  
**Implementation authority:** `FINAL_IMPLEMENTATION_PLAN.md`  
**Reviewed commit:** `5c28906` (`Added the main backend`) plus current uncommitted files

## Executive Summary

The project has a substantial backend scaffold for event ingestion, relational persistence, Redis publication, basic REST endpoints, and WebSocket broadcasting. The real ingestion-to-stream path is partly implemented and has test code, but it is not yet verified in the current environment and does not continue into operational intelligence.

The intelligence/AI area is at contract-foundation stage. A validated `Signal` model and a `MetricSnapshot` model exist, but aggregation logic, baselines, all five detectors, correlation, confidence, revenue exposure, recommendations, LangGraph orchestration, and grounded LLM explanation are not implemented. The Redis consumer explicitly uses a placeholder instead of invoking the intelligence package.

Overall status:

| Area | Status | Assessment |
|---|---|---|
| Backend scaffold | In progress | Major modules exist, but production reliability and contract alignment are incomplete. |
| Event ingestion | Partially implemented | Validation, persistence, duplicate handling, and response semantics exist. |
| PostgreSQL/outbox | Partially implemented | Durable event plus publication flag exists; full transactional-outbox recovery semantics are incomplete. |
| Redis streaming | Partially implemented | Publisher and consumer group exist; reclaim, retry, idempotent derived writes, and DLQ do not. |
| REST/WebSocket | Partially implemented | Core routes and fan-out exist; authoritative contracts and lifecycle rules are incomplete. |
| Intelligence contracts | Early progress | `Signal` is tested; `MetricSnapshot` exists but is outside the configured package and untested. |
| Deterministic intelligence | Not started | No aggregation, baseline, detector, correlation, confidence, impact, recommendation, or outcome logic. |
| LangGraph/LLM | Not started | Configuration placeholders only; no dependencies or workflow code. |
| End-to-end M0/M1 | Not achieved | Stream consumption stops at a placeholder and the simulator remains empty. |

## Evidence Reviewed

- Backend application under `app/backend/app/`
- Initial Alembic migration and SQLAlchemy models
- Backend ingestion and outbox/stream test files
- Root `Makefile`, `docker-compose.yml`, and backend dependencies
- Intelligence package configuration, `Signal`, `MetricSnapshot`, and signal tests
- Placeholder simulator and service directories
- Frozen plan and current architecture document
- Current Git status and recent history

## Backend Progress

### Implemented

#### FastAPI application lifecycle

- A FastAPI application is defined with `/health` and `/api/v1` routing.
- Startup creates a Redis client and launches outbox and stream-consumer background tasks.
- Shutdown cancels tasks and closes Redis.
- Development CORS and basic logging are configured.

#### Canonical event ingestion

- `POST /api/v1/events` validates an event envelope.
- Identical `event_id` retries return `202` with `duplicate: true`.
- Reusing an event ID with a different payload returns `409`.
- Events are persisted before dependency-managed commit.
- Missing restaurant rows are automatically provisioned for simulator convenience.
- A deterministic SHA-256 payload hash is stored.

#### Persistence schema

SQLAlchemy models and an initial Alembic migration exist for:

- restaurants;
- events;
- metric windows;
- signals;
- incidents and incident-signal links;
- recommendations;
- manager actions;
- outcomes;
- scenario runs.

This is meaningful schema coverage for the planned domain, even though several fields do not yet match the newer outlet-level intelligence contracts.

#### Redis publication and consumption

- An outbox worker polls unpublished event records.
- A publisher appends serialized envelopes to `restaurant.events`.
- A `detection` consumer group is created and reads new stream messages.
- Messages are acknowledged after the placeholder processing function returns.

#### REST and realtime surfaces

Routes exist for:

- listing restaurants;
- listing and retrieving incidents;
- submitting approve/reject/edit decisions with an idempotency key;
- resetting demo data;
- connecting to a WebSocket endpoint.

A process-local connection manager broadcasts transition messages and removes failed connections.

#### Backend test code

Tests cover:

- basic canonical-envelope validation;
- accepted ingestion;
- identical duplicate ingestion;
- conflicting duplicate rejection;
- event publication to the named Redis stream;
- consumption and acknowledgement using a mock Redis client.

### Backend Gaps and Risks

#### Critical: outlet identity is not aligned

The new intelligence contract is outlet-scoped, but the backend event envelope, database columns, logs, tests, and API responses consistently use `restaurant_id`. The persistence `Signal` also uses `restaurant_id`, `deviation`, and no signal metadata, while the domain `Signal` uses `outlet_id`, `deviation_ratio`, and metadata.

This mismatch will block clean integration and creates a risk of accidental cross-outlet correlation. The MVP contract should consistently use `outlet_id`, or explicitly model both chain-level `restaurant_id` and outlet-level `outlet_id` with all intelligence keyed to the latter.

#### Critical: stream consumer has no intelligence pipeline

`process_event_in_pipeline` is explicitly a placeholder. It logs the event and sleeps briefly. It does not:

- construct or update metric windows;
- invoke `MetricSnapshot`;
- calculate a baseline;
- run a detector;
- persist a signal;
- correlate an incident;
- calculate confidence or impact;
- start or resume LangGraph.

Therefore the current system cannot produce an incident from ingested operational evidence.

#### Critical: poison messages are discarded

On parsing or processing failure, the consumer logs the error and acknowledges the message. The frozen plan requires configurable retries followed by a named dead-letter stream. Current behavior can permanently lose failed work.

Pending-message reclamation is also absent, so a consumer crash after delivery and before acknowledgement has no implemented recovery path.

#### High: event contract differs from M1

The schema includes `inventory.updated`, which is outside the frozen M1 event list, and omits `preparation.completed`, which is required for `PREP_TIME_SPIKE`. Without preparation-completion events, the overload scenario cannot satisfy its required antecedents.

Payloads are stored as generic dictionaries after manual nested validation rather than as a discriminated Pydantic union. This weakens generated OpenAPI typing and makes downstream handling less explicit.

Naive `occurred_at` values are silently treated as UTC. The frozen contract requires an explicit UTC offset and should reject naive timestamps.

#### High: outbox is not a separate durable record

Publication state is a Boolean on `events`, not a distinct outbox table. This can support a simple demo, but concurrent workers can select the same unpublished rows and publish duplicates. There is no row claim/lock, attempt tracking, publication timestamp, or error state.

At-least-once delivery can tolerate duplicate publication only when all downstream derived writes are idempotent; those writes are not implemented yet.

#### High: decision endpoint bypasses lifecycle semantics

Approve and edit decisions immediately mark execution as `EXECUTED`; reject marks execution as `FAILED`. There is no execution adapter, LangGraph interrupt/resume, action validation, expiry check, state-transition guard, or outcome scheduling. Rejection is a decision outcome, not an execution failure.

The manager identity is hard-coded as `manager_1`.

#### High: demo reset is unsafe

The reset route deletes all events, signals, incidents, recommendations, actions, outcomes, and scenario runs before deleting synthetic restaurants. It has no demo-mode guard and does not scope deletion to validated synthetic scenario IDs. This can remove non-synthetic operational records.

#### Medium: health is not readiness

`/health` always returns a healthy application response without checking PostgreSQL, Redis, outbox backlog, or worker state. It cannot distinguish a running API process from a functioning pipeline.

#### Medium: API contracts are incomplete

- No demo-run start route exists.
- No incident outcome route exists.
- No analytics summary route exists.
- Incident listing lacks cursor pagination and most planned filters.
- WebSocket is mounted at `/api/v1/ws`, whereas the frozen plan describes `/ws?run_id=...`.
- WebSocket messages lack `run_id` and are not tied to persisted stage changes.
- Restaurant responses do not yet provide the planned outlet health/current metrics view.

#### Medium: deployment and tooling are incomplete

`docker-compose.yml` starts Redis and RedisInsight only. It does not start PostgreSQL, backend, worker, frontend, or simulator.

The `Makefile` uses Windows paths such as `app/backend/.venv/Scripts/python`, but the active workspace is macOS, where virtual environments use `.venv/bin/python`. The printed `make` commands are therefore not executable here.

Backend requirements use lower bounds rather than exact pins, and no backend lockfile is committed. This conflicts with the repository requirement to pin dependencies and commit lockfiles.

The database engine unconditionally enables SSL and asyncpg-specific prepared-statement options, making local PostgreSQL configuration less portable.

## Intelligence and AI Progress

### Implemented

#### Signal domain contract

The configured `src/` intelligence package contains an immutable Pydantic `Signal` model with:

- `outlet_id` identity;
- five frozen M1 signal types;
- bounded finite severity;
- current and baseline values;
- a documented `deviation_ratio`;
- UTC-normalized analysis windows;
- non-empty unique evidence event IDs;
- detector version;
- optional evidence metadata;
- rejection of extra fields.

Eight signal-model tests pass in the current root virtual environment.

#### Metric snapshot contract

A Pydantic `MetricSnapshot` model exists with the key M1 measurements:

- order and delivery-order counts;
- cancelled count and cancellation rate;
- average and p90 preparation minutes;
- average handoff wait;
- total, negative, and delay-related review counts;
- source event IDs;
- outlet and UTC window identity.

It validates nonnegative finite metrics, bounded cancellation rate, window ordering, subset counts, and unique source IDs.

### Intelligence and AI Gaps

#### Critical: package layout is split

The installable Hatch package uses:

`packages/intelligence/src/lossline_intelligence/`

but `MetricSnapshot` is located at:

`packages/intelligence/lossline_intelligence/aggregation/metric_snapshot.py`

Because the installed regular package resolves from `src/`, `lossline_intelligence.aggregation.metric_snapshot` cannot be imported normally. Direct file loading works, but the backend cannot consume this model through the configured package. No snapshot tests exist.

#### Critical: no deterministic intelligence implementation

Only data contracts exist. There is no code for:

- event-time aggregation;
- same-outlet historical baselines;
- baseline quality or MAD handling;
- order-volume detector;
- preparation-time detector;
- handoff-delay detector;
- cancellation detector;
- delay-review detector;
- incident correlation and deduplication;
- confidence scoring;
- estimated revenue exposure;
- rule-based recommendation selection;
- deterministic explanation fallback;
- outcome evaluation.

#### Critical: no LangGraph workflow

There is no LangGraph dependency, graph state, node implementation, checkpointer, bounded retry, approval interrupt, resume path, or workflow test. Database tables alone do not constitute workflow implementation.

#### High: no LLM integration or grounded boundary

Configuration contains optional `LLM_API_KEY` and LangSmith fields, but there is no provider integration, prompt contract, output schema, grounding validation, fallback implementation, or fake-LLM test. This is appropriately absent from deterministic calculations, but the planned explanation layer has not begun.

#### High: persistence contract conflicts with domain contract

The SQLAlchemy `Signal` schema uses float values, nullable baseline/deviation, `restaurant_id`, and `deviation`. The Pydantic domain contract uses Decimal values, required baseline/deviation ratio, `outlet_id`, and metadata. A mapper cannot currently preserve the full validated domain result.

#### High: simulator is absent

The `simulator/` directory contains only a placeholder Markdown file. There are no baseline fixtures, canonical event generator, seed handling, real HTTP ingestion runner, healthy/degraded phases, recovery behavior, or repeatability tests. The M1 intelligence cannot be calibrated or demonstrated without these inputs.

## Verification Results

Commands executed during this audit:

```text
source .venv/bin/activate && pytest -q packages/intelligence/tests
Result: 8 passed in 0.09s

source .venv/bin/activate && PYTHONPATH=app/backend pytest -q app/backend/tests
Result: test collection failed because sqlalchemy is not installed in the active environment

make -n setup dev test lint db-migrate
Result: command expansion succeeded, but all venv tool paths resolve through Windows-only Scripts/ paths
```

Interpretation:

- The `Signal` contract is verified by executable tests.
- Backend tests are present but not verified in this environment.
- No real PostgreSQL or Redis integration test was executed.
- No lint, format, type-check, migration, Docker Compose, WebSocket reconnect, LangGraph resume, simulator, or end-to-end test was demonstrated.
- The mock Redis test removes messages when read, so it does not faithfully prove Redis pending-entry or acknowledgement behavior.

## Plan Milestone Assessment

### M0 vertical slice

**Not complete.**

Working pieces include HTTP ingestion, event persistence, stream publication, a consumer shell, schema tables, REST incident reads, and WebSocket fan-out. The missing center of the slice is decisive: no detector produces a persisted signal or incident, no LangGraph path runs, and no frontend incident card exists.

### M1 lunch-rush scenario`

**Not started as an integrated scenario.**

The domain names for five signals and two foundational Pydantic contracts exist, but no simulator or deterministic pipeline implements the scenario.

## Recommended Next Sequence

1. Freeze and reconcile identity and contracts: choose `outlet_id` throughout intelligence-facing event, persistence, REST, and log models; add `preparation.completed`; align persisted `Signal` with the domain model.
2. Consolidate `MetricSnapshot` into the installable `src/lossline_intelligence/aggregation/` package and add focused validation tests.
3. Repair cross-platform setup commands, pin dependencies, commit lockfiles, and make backend plus intelligence tests runnable through root `make test`.
4. Implement a pure event-to-snapshot aggregator with UTC/local-window, zero-denominator, sparse-data, and deterministic-replay tests.
5. Implement one cancellation baseline and detector, then connect the consumer to persist the resulting signal idempotently.
6. Complete the thinnest real M0 path: one canonical cancellation event through PostgreSQL, outbox, Redis, aggregation/detection, persisted signal/incident, REST detail, and WebSocket notification.
7. Add pending-message reclaim, bounded retries, DLQ behavior, and concurrency-safe outbox claiming before claiming crash recovery.
8. Add the remaining four detectors, correlation, confidence, exposure, and recommendation rules using versioned configuration.
9. Add LangGraph only after deterministic domain stages work independently; implement checkpointed retry and approval interrupt/resume with fake LLM calls.
10. Build the seeded simulator through the real HTTP ingestion path and verify normal, degraded, abstention, approval, recovery, and outcome scenarios.

## Bottom Line

The backend has progressed from planning into a broad scaffold, especially around ingestion and persistence. The intelligence/AI subsystem has only begun at the model-contract layer. The next milestone should not be broader API or LLM work; it should be a contract-aligned, executable M0 path that turns one real ingested event stream into one deterministic persisted signal and incident without placeholders.
