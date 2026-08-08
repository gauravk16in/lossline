# LOSSLine Implementation Plan

## 1. MVP Scope

Build one complete decision loop for **Lunch Rush → Operational Overload → Cancellations** across three synthetic outlets. The MVP ingests order, preparation, cancellation, and review events; computes windowed metrics; emits deterministic signals; correlates them into an incident; recommends a rule-based action; records a manager decision; and verifies the outcome. Every UI surface must say **Synthetic data for demonstration**.

Owner: all three developers. Prerequisite: shared contracts. Done when the M1 scenario runs end to end from a clean database.

## 2. Assumptions

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, and PostgreSQL form the backend.
- A small React/TypeScript client provides the three MVP screens.
- REST plus short polling is sufficient; deployment runs one API process and one frontend.
- Event time is UTC; outlet timezone is stored separately for comparable baselines.
- The simulator may accelerate time but must preserve event timestamps and ordering.
- LLM access is optional: a deterministic template always remains available.

Owner: Person 2 records environment decisions; all approve. Done when assumptions are accepted or replaced before M0.

## 3. Non-Goals

Do not build Kafka-based streaming, microservices, autonomous detector agents, ML forecasting, a vector database, automatic operational changes, real integrations, multi-tenant billing, or a generic BI dashboard. Staffing, reservations, promotions, kitchen telemetry, and delivery-partner integrations are Phase 2.

## 4. Proposed Repository Structure

```text
apps/
  backend/app/{api,core,db,models,schemas}/
  backend/tests/{unit,integration}/
  frontend/src/{api,components,pages,types}/
services/intelligence/
  lossline_intelligence/{aggregation,detectors,correlation,scoring,recommendations,workflow}/
  tests/
simulator/
  lossline_simulator/{scenarios,generators,client}/
  tests/
docs/
```

Keep one deployable backend. `services/intelligence` is a pure domain package imported by the API, not a separately deployed service. Owner: Person 2 scaffolds backend/simulator, Person 1 intelligence, Person 3 frontend. Done when each package imports, tests, and lints independently.

## 5. Core Data Contracts

Use versioned Pydantic schemas and mirror public types in TypeScript. The normalized event is:

```json
{
  "schema_version": 1,
  "event_id": "evt_001",
  "outlet_id": "outlet_01",
  "source_type": "pos",
  "event_type": "order.completed",
  "occurred_at": "2026-08-08T07:40:00Z",
  "received_at": "2026-08-08T07:40:02Z",
  "payload": {"order_id": "ord_001", "channel": "delivery", "amount": 820.0}
}
```

Use a discriminated payload per event type: `order.created`, `order.completed`, `order.cancelled`, `preparation.completed`, and `review.received`. Reject unknown schema versions; tolerate unknown payload fields for forward compatibility. Owner: Persons 1 and 2. Done when shared fixtures validate in API and detector tests.

## 6. Database Schema

- `outlets(id, name, timezone, synthetic, created_at)`
- `events(id, event_id UNIQUE, outlet_id FK, source_type, event_type, occurred_at, received_at, payload JSONB, schema_version)`
- `signals(id, outlet_id FK, signal_type, severity, current_value, baseline_value, deviation, unit, window_start, window_end, evidence JSONB, detector_version, created_at)`
- `incidents(id, outlet_id FK, type, status, severity, confidence, probable_cause, explanation, priority, window_start, window_end, rule_version, model_version NULL, created_at, updated_at)`
- `incident_signals(incident_id FK, signal_id FK, PRIMARY KEY(...))`
- `recommendations(id, incident_id FK, action_text, urgency, expected_impact, source, rule_id, created_at)`
- `actions(id, incident_id FK, decision, original_text, final_text, decided_at, manager_note)`
- `outcomes(id, incident_id FK UNIQUE, status, before_metrics JSONB, after_metrics JSONB, evaluation_start, evaluation_end, evaluated_at)`

Index events by `(outlet_id, occurred_at)` and incidents by `(outlet_id, status)`. Keep raw events immutable and make `event_id` ingestion idempotent. Owner: Person 2. Prerequisite: contracts. Done when migrations upgrade and downgrade an empty database and constraints have integration tests.

## 7. API Contracts

- `POST /api/v1/events`: validate and persist one event; return `201`, or `200` with `duplicate: true` for an identical `event_id`; conflicting duplicates return `409`.
- `GET /api/v1/outlets`: list outlet health summaries and active-incident counts.
- `GET /api/v1/incidents`: filter by outlet/status; return newest first with pagination.
- `GET /api/v1/incidents/{id}`: incident, evidence, recommendation, action, and outcome.
- `POST /api/v1/incidents/{id}/actions`: submit `APPROVE`, `REJECT`, or `EDIT`, final text, and optional note. This replaces separate approve/reject endpoints to prevent duplicated behavior.
- `GET /api/v1/incidents/{id}/outcome`: return evaluation or `INSUFFICIENT_DATA` with the next eligible evaluation time.
- `POST /api/v1/analysis/run`: demo-only trigger for pending windows; protect or disable outside demo mode.

Generate OpenAPI and a typed frontend client. Owner: Person 2; Person 3 reviews response shapes. Done when examples and status/error responses pass contract tests.

## 8. Event Ingestion Flow

Validate envelope → validate event-specific payload → normalize enums/UTC/units → check idempotency → persist → mark the relevant outlet/window dirty → return promptly. M0 may analyze synchronously after persistence; M1 should process dirty windows through an in-process scheduled job so ingestion latency is independent of analysis. Late events recompute only affected open windows. Quarantine invalid simulator events in simulator logs rather than storing malformed data.

Owner: Person 2. Prerequisite: migrations and schemas. Done when valid, invalid, duplicate, conflicting, and late-event cases are tested.

## 9. Aggregation and Baselines

Use aligned 30-minute analysis windows. Produce order count, delivery order count, cancellation rate (`cancelled / created`), mean and p90 preparation minutes, mean handoff wait, negative-review count, and delay-keyword count. Require minimum denominators (for example, 10 created orders) before rate signals.

Baseline each metric against the median of the same outlet and local half-hour across the previous seven synthetic days. Use median absolute deviation (MAD) for dispersion; when MAD is zero, apply a configured business threshold. A two-hour wider window is attempted once when initial confidence is below `0.50`.

Owner: Person 1. Prerequisite: event queries and outlet timezone. Done when fixtures prove window boundaries, sparse data, zero baseline, and late-event behavior.

## 10. Specialist Detectors

Each pure detector accepts a metric snapshot plus baseline and returns zero or one signal:

- `ORDER_VOLUME_SPIKE`: deviation ≥ 30% and robust z-score ≥ 2.
- `PREP_TIME_SPIKE`: mean increase ≥ 40% or p90 exceeds the configured SLA.
- `CANCELLATION_SPIKE`: rate increase ≥ 5 percentage points and ≥ 2× baseline.
- `DELAY_REVIEW_SPIKE`: at least two negative reviews with delay keywords in-window.

Severity is normalized to `[0,1]` from threshold exceedance and capped. Stockout and external-context detectors are SHOULD HAVE only after M1. Owner: Person 1. Done when threshold, just-below-threshold, missing-data, and deterministic-repeat tests pass.

## 11. Signal Format

A signal contains stable type, outlet, severity, current/baseline values, deviation and unit, window, detector version, and structured evidence event IDs. It must never contain prose as its only evidence. Persist each `(outlet, type, window_end, detector_version)` once.

Owner: Person 1; Person 2 persists it. Done when API incident evidence can be traced from signal to source events.

## 12. Correlation Algorithm

Group signals by outlet whose windows overlap or end within 60 minutes. Match an ordered rule table. The MVP overload rule requires `ORDER_VOLUME_SPIKE + PREP_TIME_SPIKE + CANCELLATION_SPIKE`; `DELAY_REVIEW_SPIKE` strengthens but does not gate it. Merge with an existing open incident of the same type when windows are contiguous; otherwise create a candidate. Never correlate across outlets.

Owner: Person 1. Prerequisite: signals. Done when positive, missing-required-signal, temporally separated, cross-outlet, and duplicate tests pass.

## 13. Deterministic Confidence Algorithm

Calculate and persist components:

```text
severity       = weighted mean of required signal severities
coverage       = present weighted evidence / total rule weight
alignment      = max(0, 1 - signal-span-minutes / 120)
data_quality   = mean(completeness, sample_sufficiency, freshness)
confidence     = min(0.95,
  0.35*severity + 0.30*coverage + 0.20*alignment + 0.15*data_quality)
```

Use weights: cancellation `.35`, prep `.30`, volume `.20`, reviews `.15`. Do not add historical similarity until comparable labeled incidents exist. Below `.50`, rerun once using two hours; if still low, persist `MONITORING` with insufficient evidence. Store formula version and components for auditability.

Owner: Person 1. Done when boundary values map correctly to monitor (`<.50`), review (`.50–.74`), and high-confidence alert (`.75–.95`).

## 14. Incident Lifecycle

```text
MONITORING → OPEN → ACTION_APPROVED → EVALUATING → RESOLVED
                    ↘ ACTION_REJECTED → CLOSED
OPEN → CLOSED (manual/demo reset)
```

`OPEN` covers both review and high-confidence priority bands. Enforce transitions in one domain service and record timestamps. An edit counts as approval of the edited action. Owner: Person 2, rules reviewed by Person 1. Done when invalid transitions return `409` and every valid transition is tested.

## 15. LLM Explanation Layer

Define an `ExplanationProvider` interface receiving only incident type, confidence components, and structured evidence. Require a small JSON response (`headline`, `probable_cause`, `evidence_summary`) and prohibit causal certainty. Validate output, reject unsupported numbers, and fall back to deterministic templates on timeout, parse failure, or missing credentials. Do not send customer review identities.`

Owner: Person 1. Prerequisite: stable incident evidence. Done when mocked success/failure paths work and every rendered claim maps to evidence. This is SHOULD HAVE; templates unblock M1.

## 16. Recommendation Engine

Use a versioned rule map. `OPERATIONAL_OVERLOAD` returns: reduce incoming delivery load temporarily, increase displayed preparation estimates, and prioritize the existing queue. Include urgency, expected metric effect, and `source=RULE`. LLM fallback is Phase 2 because advisory text without a reviewed rule increases demo risk.

Owner: Person 1. Done when known rules are deterministic and an unknown incident returns a safe “manager review required” recommendation.

## 17. Manager Approval Flow

The UI submits approve, reject, or edited approval with an optional note. The backend validates lifecycle state, stores both suggested and final text, and starts the outcome clock only for approved/edited actions. No endpoint executes a real restaurant change.

Owner: Person 3 UI, Person 2 API. Done when refresh preserves the decision and repeated submission is idempotent.

## 18. Outcome Verification

Capture the incident window as “before.” After approval, wait for a comparable 30-minute window, then compare cancellation rate and preparation time while checking order volume. Classify:

- `IMPROVED`: cancellation rate drops ≥ 20% and prep time does not worsen > 10%.
- `WORSENED`: either primary metric worsens ≥ 15%.
- `UNCHANGED`: sufficient data but neither condition applies.
- `INSUFFICIENT_DATA`: fewer than 10 orders or the window is incomplete.

Display raw before/after values and rules; do not claim the action caused the change. Owner: Person 1 algorithm, Person 2 persistence, Person 3 presentation. Done when all four outcomes have fixtures.

## 19. Synthetic-Data Generator

Use a seeded clock and random generator. Create seven baseline days plus a scripted demo day: 30 minutes healthy, 30 minutes demand surge, 30 minutes prep/handoff degradation, cancellations and delayed reviews, manager action, then recovery. Provide `baseline`, `lunch-rush`, `recovery`, and `full-demo` commands with adjustable API URL and speed. Replays with the same seed produce identical IDs and values.

Owner: Person 2. Prerequisite: event contract. Done when `full-demo` creates the expected incident and recovery without manual database edits.

## 20. Frontend Integration

Build three focused routes: outlet health, incident detail, and action/outcome. Poll summaries every five seconds during the demo; stop polling hidden tabs. Show confidence band and components, evidence values with units/times, action controls, and before/after outcome cards. Include loading, empty, stale, and API-error states.

Owner: Person 3. Prerequisite: approved API examples; use fixtures until endpoints land. Done when the complete scenario is navigable at laptop and projector widths.

## 21. LangGraph State and Nodes

LangGraph is SHOULD HAVE, not an M0 blocker. If used, state contains `outlet_id`, window bounds, snapshots, signals, candidate, score components, explanation, recommendation, and errors. Nodes are `aggregate`, parallel pure `detect_*`, `correlate`, `score`, optional one-time `widen_window`, `explain`, `recommend`, and `persist`. Conditional edges enforce the single retry. Business logic remains callable without LangGraph.

Owner: Person 1. Done when graph and direct orchestration produce equivalent results for the golden fixture.

## 22. Error Handling

Return RFC 9457-style problem details with a request ID. Separate validation (`422`), missing (`404`), state conflict (`409`), and dependency failure (`503`). A failed explanation must not discard a valid incident. Make analysis rerunnable and database writes transactional per window.

Owner: Person 2. Done when failures are visible, retry-safe, and covered by integration tests.

## 23. Observability and Tracing

Emit structured logs with request, outlet, event, window, and incident IDs; record ingestion count/latency, invalid events, analysis duration, detector firing counts, and LLM failures. Use OpenTelemetry-compatible hooks if inexpensive. LangSmith/Langfuse is optional and only traces the explanation boundary, with payload redaction.

Owner: Person 2 platform, Person 1 intelligence spans. Done when a demo incident is traceable from event ingestion to outcome using IDs.

## 24. Test Strategy

Use pytest for backend/intelligence/simulator, database integration tests against PostgreSQL, and the frontend’s standard unit runner plus Playwright for one golden flow. Freeze clocks and seed randomness. Maintain contract fixtures under a shared test-data directory. CI runs format, lint, type-check, unit, integration, frontend build, and the deterministic scenario smoke test.

No blanket coverage target should substitute for behavior; require full branch coverage for confidence, lifecycle, and outcome classification. Owner: each developer for owned code. Done when CI is green from a clean checkout.

## 25. Security Considerations

Keep secrets in environment variables with a sanitized `.env.example`; validate payload size and enum values; use parameterized ORM queries; configure explicit CORS origins; redact review author data and LLM payloads; and protect demo-only analysis/reset endpoints. Authentication is SHOULD HAVE for a public deployment and may be a fixed demo user locally.

Owner: Person 2. Done when no secrets are committed and basic abuse/error cases are tested.

## 26. Three-Person Ownership

- **Person 1 — Intelligence + Integration:** metrics, baselines, detectors, correlation, scoring, rules, outcomes, explanation abstraction, optional graph.
- **Person 2 — Backend + Simulator:** repository tooling, database, ingestion, APIs, jobs, observability, simulator, deployment configuration.
- **Person 3 — Frontend + Demo:** typed client, three screens, polling, evidence visualization, action flow, outcome view, demo script.

Shared ownership is limited to contracts, golden fixtures, and end-to-end acceptance to avoid ambiguous implementation responsibility.

## 27. Dependencies Between Teammates

Freeze event/signal/incident/action examples first. Person 1 can then implement against in-memory fixtures while Person 2 builds persistence and Person 3 builds against mocked API responses. Integrate in this order: event contract → persisted event → metric snapshot → signal → incident response → action → outcome. Contract changes require all three reviewers after M0.

## 28. Milestone Execution

- **M0 — Vertical slice (MVP):** one event type, one detector, one persisted incident, incident API, one frontend card.
- **M1 — Lunch-rush loop (MVP):** all four detectors, correlation, confidence, recommendation, manager decision, recovery, outcome.
- **M2 — Demo hardening (SHOULD HAVE):** explanation provider, optional LangGraph, observability, error states, reproducible setup and rehearsed demo.
- **M3 — Expansion (PHASE 2):** real connectors, additional detectors, auth/tenancy, learned baselines, asynchronous infrastructure only when load proves necessary.

Each milestone ends with a clean-database demonstration and automated golden-path test.

## 29. Exact First Tasks

**Person 1:** define metric snapshot and signal schemas; create golden baseline/surge fixtures; implement cancellation metric and detector; specify scoring component tests.

**Person 2:** initialize Python workspace and quality tooling; add local PostgreSQL setup and first migration; implement event schemas and `POST /events`; create seeded single-event simulator command.

**Person 3:** initialize React/TypeScript app; codify API mock types/examples; build the synthetic-data banner and incident summary card; add loading/empty/error states.

First integration check: simulator posts an event, database stores it, a cancellation detector creates an incident, and the UI renders it.

## 30. MVP Completion Checklist

- [ ] Clean setup is documented and reproducible.
- [ ] All synthetic metrics are visibly labeled.
- [ ] Shared versioned event contract rejects invalid data and handles duplicates.
- [ ] Baseline and lunch-rush scenario replay deterministically.
- [ ] Required detectors produce traceable signals.
- [ ] Correlation never crosses outlet or time bounds.
- [ ] Confidence is deterministic, versioned, explainable, and capped at `.95`.
- [ ] Explanation contains no unsupported claims and has a template fallback.
- [ ] Recommendation is rule-sourced and advisory.
- [ ] Approve, reject, and edit transitions persist correctly.
- [ ] Outcome shows raw metrics and all four classifications.
- [ ] Three frontend screens handle normal and error states.
- [ ] Golden end-to-end test and CI pass from a clean checkout.

## A. Build Order

1. Agree on schemas, enums, fixtures, thresholds, and acceptance scenario.
2. Scaffold workspaces, local database, linting, typing, testing, and CI.
3. Migrate outlets/events and implement idempotent ingestion.
4. Generate and ingest deterministic baseline events.
5. Implement aggregation and one cancellation detector.
6. Persist signals/incidents and expose incident APIs.
7. Render the first incident card to complete M0.
8. Add volume, prep-time, and delay-review detectors.
9. Add correlation, confidence components, and recommendation rules.
10. Complete incident investigation and action UI/API.
11. Add recovery generation and outcome verification.
12. Add grounded explanations, optional LangGraph, observability, and demo hardening.

## B. Parallel Team Board

| Stage | Person 1 | Person 2 | Person 3 | Integration Check |
|---|---|---|---|---|
| Contracts | Signal/metric schema | Event/API/schema draft | UI response review | Golden JSON validates everywhere |
| M0 | Cancellation detector | Ingestion, DB, incident API, simulator | Incident card with mocks | One real incident renders |
| M1 detection | Remaining detectors, correlation, score | Analysis job and persistence | Investigation screen | Lunch-rush evidence agrees |
| Decision | Rules and outcome algorithm | Action/outcome APIs | Controls and outcome screen | Approval leads to evaluation |
| Hardening | Explanation/graph | Logs, errors, deployment | UX/error polish, demo script | Clean full-demo rehearsal |

## C. Architecture Inputs Still Needed

The eventual `ARCHITECTURE.md` must finalize:

- frontend framework/build tool and Python dependency manager;
- local, CI, and hosted PostgreSQL strategy;
- synchronous versus scheduled in-process analysis trigger;
- deployment target, process topology, and HTTPS/auth boundary;
- contract/versioning and migration compatibility policy;
- exact baseline history, thresholds, SLA values, and business-impact formula;
- LLM provider policy, data retention/redaction, timeout, and cost ceiling;
- polling interval and future criterion for server push;
- incident deduplication/closure rules and late-event watermark;
- observability backend, retention, alerting, and demo reset procedure;
- criteria that justify extracting workers or services after the MVP.

Finalize these after M0 exposes real constraints; do not turn provisional implementation choices into distributed architecture prematurely.
