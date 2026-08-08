# LOSSLine Architecture

## Purpose

LOSSLine detects operational degradation at restaurant outlets, explains the supporting evidence, recommends a bounded action, requires manager approval, and verifies the outcome. The MVP is a modular monolith designed for deterministic replay and a repeatable synthetic lunch-rush demonstration.

`FINAL_IMPLEMENTATION_PLAN.md` is the implementation authority. This document summarizes its system boundaries and runtime flow; it does not replace the detailed contracts, configuration ledger, or decision records.

## Architectural P`rinciples

- Correlation is outlet-scoped. Signals and incidents from different `outlet_id` values must never correlate.
- PostgreSQL is durable truth for accepted events, derived state, decisions, and outcomes.
- Redis Streams provides asynchronous delivery, not authoritative storage.
- REST is authoritative UI state. WebSocket messages report transient progress and prompt REST refreshes.
- Operational metrics, anomaly detection, correlation, confidence, impact, recommendations, and outcomes are deterministic and versioned.
- LLM output may help phrase a grounded explanation, but it never calculates metrics, confidence, revenue exposure, recommendation selection, or outcome status.
- The simulator uses the production ingestion contract and never writes directly to storage or the stream.
- Numeric defaults are configuration, not business facts.

## System Context

```text
Synthetic simulator
        |
        | canonical events over HTTP
        v
FastAPI backend ---- REST/WebSocket ---- Operator dashboard
        |
        | transaction
        v
PostgreSQL + outbox
        |
        | outbox publication
        v
Redis Stream: restaurant.events
        |
        | consumer group: detection
        v
Deterministic intelligence pipeline
        |
        v
LangGraph investigation and approval workflow
        |
        v
PostgreSQL authoritative state
```

The stream name `restaurant.events` is retained for the MVP contract. Event processing and correlation use `outlet_id` as the operational identity.

## Deployable Boundaries

The MVP remains a modular monolith:

- `apps/backend/` contains FastAPI endpoints, persistence, the outbox publisher, stream consumers, REST state APIs, and WebSocket notifications.
- `apps/frontend/` contains the operator dashboard, incident evidence, approval actions, and outcome views.
- `packages/intelligence/` or `services/intelligence/` contains pure aggregation, baseline, detection, correlation, confidence, impact, recommendation, and workflow-domain logic. Repository packaging must converge on one location before broader implementation.
- `simulator/` contains seeded baseline data and repeatable scenarios that submit canonical events to FastAPI.
- `docs/` contains contracts, decisions, runbooks, and demo guidance.

The backend imports the intelligence package. The frontend and simulator run as separate processes. These are code-ownership boundaries, not independently deployed microservices.

## Authoritative Event Flow

1. The simulator or another producer submits a versioned canonical event to FastAPI.
2. FastAPI validates identifiers, the event discriminator, typed payload data, and an offset-aware occurrence timestamp.
3. One PostgreSQL transaction stores the canonical event and an outbox record.
4. The API acknowledges only durable acceptance. An identical event retry is idempotent; a conflicting reuse of an event ID is rejected.
5. The outbox publisher appends the normalized event to `restaurant.events` and marks the outbox record published.
6. The `detection` consumer group reads the message and updates its affected event-time window.
7. The intelligence pipeline derives snapshots, signals, and possibly an incident.
8. Derived state is committed before the stream message is acknowledged.
9. Persisted stage transitions may produce display-safe WebSocket notifications.
10. The frontend reloads authoritative objects through REST.

Delivery is at least once. Derived writes must therefore be idempotent by outlet, window, result type, and configuration or rule version. Consumer failures leave messages claimable; Redis failures leave durable outbox work pending.

## Intelligence Pipeline

```text
canonical outlet events
        |
        v
MetricSnapshot
        |
        +---- historical matching windows ----> baseline
        |                                       |
        +---------------------------------------+
        v
deterministic detectors
        |
        v
validated Signals
        |
        v
outlet-scoped temporal correlation
        |
        v
deterministic confidence and exposure
        |
        v
rule-selected recommendation
        |
        v
LangGraph investigation / approval / verification
```

### Aggregation

A `MetricSnapshot` represents exactly one outlet and one analysis window. It contains order and delivery counts, cancellation count and rate, average and p90 preparation time, average handoff wait, review counts, and source event IDs. Aggregation does not detect anomalies or perform workflow actions.

The configured MVP window is event-time based. Local outlet timezone is used when selecting historical comparison windows; stored timestamps normalize to UTC. Sparse data and zero denominators produce explicit insufficiency rather than fabricated values.

### Baselines and Detectors

Baselines use matching historical windows for the same outlet. Detectors compare the current snapshot with a baseline snapshot and may emit these signal types:

- `ORDER_VOLUME_SPIKE`
- `PREP_TIME_SPIKE`
- `HANDOFF_DELAY_SPIKE`
- `CANCELLATION_SPIKE`
- `DELAY_REVIEW_SPIKE`

Signals retain source event IDs for traceability and optional metadata describing sample size, threshold, and baseline method. `deviation_ratio` has one meaning across detectors: `(current_value - baseline_value) / baseline_value`.

### Correlation and Confidence`

Correlation combines temporally aligned signals only when every signal has the same `outlet_id`. The overload rule requires order-volume and preparation evidence plus handoff-delay or cancellation impact evidence; delay reviews strengthen corroboration. Versioned fingerprints and persisted signal links suppress duplicate incidents.

Confidence is calculated from persisted evidence strength, coverage, temporal alignment, and data quality. An LLM cannot create or alter the score. Missing or non-finite inputs cause abstention or an insufficient-data result.

### Recommendation and Workflow

Recommendations come from versioned deterministic rules. LangGraph coordinates post-detection investigation, one bounded evidence retry, persistence, manager approval interruption/resume, and outcome verification. It does not replace the underlying calculations.

Actions are never silently executed. Approval, rejection, or edited approval is recorded with an idempotency key and audit timestamps. Outcome evaluation compares deterministic post-action metrics with the stored baseline and records improvement, resolution, failure, or insufficient data.

## State and Persistence

PostgreSQL stores:

- outlets and their timezone/currency configuration;
- canonical events and payload hashes;
- outbox publication state;
- metric windows and baseline-quality data;
- signals and their evidence event IDs;
- incidents and linked signals;
- confidence components and estimated exposure inputs;
- recommendations, manager actions, and execution state;
- outcomes and evaluation times;
- synthetic scenario runs.

Domain results such as `Signal` remain free of database metadata where practical. Persistence models add identifiers, creation/update timestamps, uniqueness constraints, and foreign keys.

## API and Realtime Boundary

REST exposes event ingestion, outlet health, incident feeds and details, manager decisions, outcomes, analytics required by the MVP, and demo controls. Contracts are versioned under `/api/v1` and invalid requests use structured problem details.

WebSocket messages contain transition identifiers, stage, status, and occurrence time. They do not contain the only copy of domain state. On disconnect, the UI shows reconnecting and refreshes through REST after connection recovery.

## Reliability and Failure Behavior

| Failure | Required behavior |
|---|---|
| PostgreSQL unavailable | Fail readiness and reject ingestion without claiming acceptance. |
| Redis unavailable | Preserve accepted work in the outbox and report delayed processing. |
| Publisher crash | Retry unpublished outbox records. |
| Consumer crash | Reclaim pending stream messages and rely on idempotent writes. |
| Duplicate delivery | Produce no duplicate event, signal, or incident. |
| Late or out-of-order event | Store it, apply configured lateness policy, and never silently reopen resolved incidents. |
| Sparse evidence or baseline | Abstain or return `INSUFFICIENT_DATA`. |
| LLM failure | Use a deterministic explanation template. |
| WebSocket failure | Recover authoritative state through REST. |

Poison messages move to a named dead-letter stream only after the configured retry limit. Remote tracing failures never block processing.

## Security and Data Handling

- Secrets and provider credentials belong in ignored environment files; only sanitized examples are committed.
- Incoming events use typed schemas and bounded payload sizes.
- Credentials and unredacted sensitive payloads must not be logged.
- Demo reset is enabled only in demo mode and may delete only records associated with validated synthetic scenario runs.
- Synthetic metrics and estimated exposure are labeled as such. Estimated exposure must not be presented as observed profit loss or causal certainty.

## Observability

Structured logs carry request, event, stream message, scenario run, outlet, window, incident, graph run, and action identifiers when available. Operational metrics cover ingestion results, outbox backlog, Redis pending messages, processing latency, detector firings, incident deduplication, graph stages, WebSocket connections, approval latency, fallbacks, and outcomes.

An incident must be traceable from its persisted result back through signals and metric snapshots to canonical source events.

## Deployment

The intended local deployment uses Docker Compose with frontend, backend, worker, PostgreSQL, and Redis containers on one demo machine. The worker owns stream consumption and outcome scheduling. A single backend replica may use in-process WebSocket fan-out; multiple replicas would require a shared fan-out mechanism and distributed scheduler ownership.

All thresholds, window sizes, evidence weights, retry limits, lateness rules, action expiry, outcome timing, and scenario speed are versioned configuration. Dependency versions are pinned and lockfiles are committed.

## Verification Boundaries

- Unit tests cover every deterministic aggregation, detector, correlation, confidence, impact, recommendation, and outcome rule.
- Contract tests cover canonical events, OpenAPI payloads, and frontend types.
- Integration tests cover PostgreSQL migrations/outbox, Redis replay and idempotency, LangGraph resume, REST state, and WebSocket reconnect.
- One seeded lunch-rush scenario traverses the real ingestion path and produces exactly one reproducible overload incident.
- Normal and near-threshold scenarios produce no incident; sparse evidence demonstrates abstention.
- Automated tests fake LLM calls.

## Deferred Beyond the MVP

The MVP does not introduce microservices, cross-outlet correlation, autonomous action execution, LLM-derived business calculations, learning recommendations from stored outcomes, or a durable WebSocket event log. These require explicit architectural decisions rather than incremental additions to the current modules.
