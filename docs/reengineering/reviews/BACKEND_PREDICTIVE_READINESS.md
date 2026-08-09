# Backend Predictive Readiness Audit

Author: Person B (Product/Platform)

Audit date: 2026-08-09

Status: COMPLETE — gaps mapped to owning chunks

## Executive summary

The `apps/backend/` codebase is a functioning reactive pipeline. It has no predictive persistence tables, no forecast APIs, no service-window configuration, and no durable LangGraph orchestration. All predictive capabilities require additive implementation. The reactive path continues operating during the transition.

## Detailed gap analysis

### Database layer (`apps/backend/src/db/`)

| Area | Current state | Gap | Resolution chunk | Notes |
|---|---|---|---|---|
| `outlet_id` vs `restaurant_id` | All 7 tables use `restaurant_id` as column name and FK target | New predictive tables use `outlet_id`; reactive tables keep `restaurant_id` during coexistence | C04 (new tables) / C19 (full migration) | `Restaurant.id` column name is fine — only the table name and FK references say "restaurant" |
| `NormalizedSignal` table | Absent | Need `normalized_signals` table with typed value, quality, provenance, effective interval, entity, dimensions | C04 | Separate from reactive `signals` table |
| `FeatureSnapshot` table | Absent | Need `feature_snapshots` table with immutable versioned rows, fingerprint, source signal IDs | C04 | Schema depends on C03 frozen contract |
| `ForecastResult` table | Absent | Need `forecast_results` table with grain, as-of, point/lower/upper, model version | C08/C19 | Person B implements after C05 freezes contract |
| `InventoryProjection` table | Absent | Need `inventory_projections` with forecast reference, supply/demand, shortage/surplus scenarios | C08 | Person B owns C08 |
| `CapacityProjection` table | Absent | Need `capacity_projections` with forecast reference, utilization, queue, risk tier | C09 | Person B owns C09 |
| `RiskCandidate` table | Absent (reactive `incidents` is semantically different) | Need `risk_candidates` with typed risk, grain, evidence IDs | C19 | After C08/C09 risk types are frozen |
| `DriverEvidence` table | Absent | Need `driver_evidence` with feature reference, rank, direction, contribution | C10/C19 | Person B supports C10 integration |
| `ForecastDossier` table | Absent | Need `forecast_dossiers` with immutable reference assembly | C11/C19 | Person A owns C11 contract |
| `DecisionCandidate` table | Absent (reactive `recommendations` + `actions` are different) | Need `decision_candidates` with dossier reference, action enum, quantity, evidence | C14/C19 | After C12–C14 agent tools freeze |
| `GuardResult` table | Absent | Need `guard_results` with submitted/final decision, violations, disposition | C14/C19 | After C14 guard contract |
| `DecisionTrace` table | Absent (reactive incident carries partial trace) | Need `decision_traces` linking full provenance chain | C19 | Full integration artifact |
| `ActualOutcome` table | `outcomes` exists but stores reactive status | Need `actual_outcomes` with matured demand, fulfilled/unfulfilled, censoring | C21 | Person A owns C21 contract |
| Alembic migrations | Exist for reactive tables | Need new migration(s) for each predictive table | Per-chunk | Each chunk that adds a table creates its migration |

### API layer (`apps/backend/src/api/`)

| Area | Current state | Gap | Resolution chunk |
|---|---|---|---|
| Event ingestion | `POST /api/v1/events` — works with reactive event types | May need new event types for SKU-level demand, inventory, capacity snapshots | C03/C04 |
| Forecast read API | Absent | `GET /api/v1/forecasts/{outlet_id}/{window}` | C19 |
| Projection read API | Absent | `GET /api/v1/projections/inventory/{id}`, `/capacity/{id}` | C19 |
| Dossier read API | Absent | `GET /api/v1/dossiers/{id}` | C19 |
| Decision submission API | Absent for predictive path | `POST /api/v1/decisions` with typed `DecisionCandidate` | C19 |
| Outcome comparison API | Absent | `GET /api/v1/evaluations/forecast/{id}` | C21 |
| Analytics summary | Returns reactive incident counts only | Need forecast accuracy, risk detection, and decision metrics | C19/C20 |
| WebSocket | Broadcasts reactive stage transitions | Need predictive artifact transitions (forecast computed, risk detected, decision submitted) | C16/C19 |

### Intelligence orchestration (`apps/backend/src/intelligence/`)

| Area | Current state | Gap | Resolution chunk |
|---|---|---|---|
| `pipeline.py` | Reactive detection pipeline (aggregation → detect → correlate → score → recommend) | Need predictive pipeline (normalize → snapshot → forecast → project → risk → dossier → agent → guard) | C16/C19 |
| `persistence.py` | Reactive domain type persistence (Signal, Incident, Recommendation) | Need predictive artifact persistence module | C04 onwards |
| `langgraph_workflow.py` | Placeholder stages — narrates already-computed results | Durable artifact orchestration with real transitions | C16 |
| `windows.py` | UTC-aligned 30-minute windows | Named service windows in outlet timezone | C04 |
| `mapper.py` | Maps between reactive domain and DB types | Need predictive artifact mappers | C04 onwards |
| `explanations.py` | Reactive explanation with LLM/fallback | Grounded explanation from frozen dossier | C17 |
| `outcomes.py` | Reactive metric comparison | Forecast-vs-actual evaluation | C21 |
| `event_loader.py` | Loads events for reactive aggregation | May need to load events for signal normalization | C04 |

### Configuration (`apps/backend/src/config.py`)

| Setting | Current | Needed | Resolution chunk |
|---|---|---|---|
| `WINDOW_MINUTES` | 30 | Named service window configuration | C04 |
| Forecast model settings | Absent | Model version, checkpoint path, feature registry version | C06/C19 |
| Projection settings | Absent | Safety buffer, replenishment, capacity parameters | C08/C09 |
| Agent settings | Absent | Tool budget, repair limit, decision timeout | C12–C14 |
| Retrieval settings | Absent | Structured query limits, document retrieval toggle | C15 |

### Frontend (`apps/frontend/`)

| Area | Current state | Gap | Resolution chunk |
|---|---|---|---|
| TypeScript types | Mirrors reactive Python models only | Need predictive types: `ForecastResult`, `InventoryProjection`, `CapacityProjection`, `RiskCandidate`, `ForecastDossier`, `DecisionCandidate` | C20 (after C19 API freeze) |
| Mock data | `mock.ts` — hardcoded revenue, capacity, timing, incidents, shifts, service flow, chain metrics | Replace with API calls to frozen schemas | C20 |
| Dashboard | Incident-focused | Forecast-first: SKU demand, stockout risk, capacity utilization, driver attribution | C20 |
| Predictive Today view | Absent | Forecast vs. actual, upcoming risks, decision history | C20 |

### Infrastructure

| Area | Current state | Gap | Resolution chunk |
|---|---|---|---|
| Docker Compose | Postgres + Redis + backend + frontend | May need model artifact volume, checkpoint storage | C19 |
| Dockerfile (backend) | Python + FastAPI | May need model dependencies (lightgbm/xgboost) | C06/C19 |
| Alembic | Configured for reactive schema | Needs migration per predictive table | Per-chunk |

## Assets preserved (no changes)

The following work correctly for the reactive path and will remain untouched:

- Event ingestion and duplicate detection (`POST /api/v1/events`)
- PostgreSQL/Redis/outbox boundaries
- Restaurant auto-provisioning
- Incident, recommendation, action, outcome reactive lifecycle
- Manager approval with idempotency and expiry
- WebSocket notification infrastructure
- Existing Alembic migrations
- Backend tests
- React application shell and API client

## Readiness summary

| Phase | Person B readiness | Blocking dependency |
|---|---|---|
| Phase 1 (C02) | Ready to review — no backend work needed | C02 contracts from Person A |
| Phase 2 (C03/C04) | Ready after C03 contract freeze | C03 dataset contract |
| Phase 3 (C05–C10) | C08/C09 ready after C05 forecast contract | C05 `ForecastResult` contract |
| Phase 4 (C11) | Review only — no backend work | C11 `ForecastDossier` contract |
| Phase 5 (C12–C15) | C15 ready after C11 freeze | C11 dossier contract |
| Phase 6 (C16–C18) | C16 ready after C14 freeze | C14 guarded-decision contract |
| Phase 7 (C19–C21) | C19 ready after C16+C17+C18 | All upstream chunks |
| Phase 8 (C22) | Shared with Person A | C19+C20+C21 |
