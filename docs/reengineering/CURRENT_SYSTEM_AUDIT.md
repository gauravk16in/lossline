# Current LOSSLine System Audit

Audit date: 2026-08-09

## Executive finding

LOSSLine currently implements a functioning reactive anomaly-and-incident demo. It detects degradation after operational symptoms appear. It has no executable outlet × SKU × future-window demand forecast, trained forecasting artifact, point-in-time dataset, inventory projection, structured driver attribution, or forecast evaluation loop.

## Executable flow

```text
Seeded lunch-rush simulator
  → POST /api/v1/events
  → PostgreSQL event/outbox persistence
  → Redis stream or inline processing
  → 30-minute event aggregation
  → contiguous-window history plus fixture fill
  → five deterministic anomaly detectors
  → operational-overload correlation
  → deterministic evidence score and revenue extrapolation
  → fixed playbook
  → mostly stage-recording LangGraph
  → LLM or template explanation
  → manager decision
  → scripted recovery events
  → coarse outcome status
  → incident-oriented React UI and standalone HTML demo
```

## Capability classification

| Capability | Classification | Executable finding |
|---|---|---|
| Event ingestion and validation | REAL | Typed event envelope, persistence, duplicate detection, conflict handling and normal API path exist |
| PostgreSQL persistence | REAL | Events, signals, incidents, recommendations, actions, outcomes and scenario runs are persisted |
| Redis/outbox path | REAL | Asynchronous publication and consumption boundary exists; inline mode is also supported |
| Simulator | SYNTHETIC BUT COMPUTED | Seeded scripted scenario calls the normal event API |
| Simulator causal world | HARDCODED | Trajectory and recovery are scripted to generate the intended incident; SKU demand is not modeled as a latent process |
| Window aggregation | REAL | Computes order, cancellation, preparation, handoff and review metrics |
| Baseline calculation | REAL | Median and MAD logic is deterministic and sparse-aware in the package |
| Backend history selection | BROKEN | Uses contiguous preceding UTC windows, not comparable local weekday/service windows |
| Fixture baseline filling | HARDCODED | Module/config defaults fill missing history |
| Sparse-history truthfulness | BROKEN | `merge_baseline_with_fixture()` sets `sufficient_history=True` regardless of computed sufficiency |
| Five anomaly detectors | REAL | Deterministic, versioned and repeatable threshold detectors |
| Incident correlation | REAL but narrow | Produces operational overload only and returns one qualifying candidate per call |
| Evidence confidence | SYNTHETIC BUT COMPUTED | Deterministic anomaly evidence score; it is not forecast uncertainty or calibrated correctness |
| Revenue exposure | SYNTHETIC BUT COMPUTED | Extrapolates current order/cancellation behavior for 60 minutes; it is not a demand forecast |
| Recommendation | HARDCODED | One rule-selected overload playbook; not SKU-, quantity-, inventory- or capacity-aware |
| LangGraph `load_context` | PLACEHOLDER | Validates supplied evidence and retrieves nothing |
| LangGraph confidence stages | PLACEHOLDER | Append stage names; confidence was computed before graph entry |
| LangGraph context widening | PLACEHOLDER | Increments a retry count without retrieving or recomputing evidence |
| LangGraph recommendation stage | PLACEHOLDER | Recommendation selection occurred before graph entry |
| Explanation provider | REAL but limited | Typed provider boundary and deterministic fallback exist |
| Numeric grounding | REAL but incomplete | Numeric tokens are checked against evidence; semantic claims are not comprehensively grounded |
| Fallback explanation | HARDCODED | Fixed wording is assembled from signal presence |
| Demand forecasting | UNUSED/ABSENT | No forecast at outlet × SKU × future service-window grain |
| Feature registry | PARTIAL, uncommitted | C1 working-tree signal registry exists; feature definitions and transformations do not |
| Point-in-time dataset | ABSENT | No training table, target construction or leakage-tested join pipeline |
| Trained model | ABSENT | No training pipeline, model artifact, registry, checksum or accepted model loader |
| Forecast evaluation | ABSENT | No chronological split, forecast metrics, subgroup report or acceptance gate |
| External context | ABSENT | Weather forecast vintages, holidays, festivals and local events do not enter intelligence |
| Inventory intelligence | ABSENT | Inventory values in simulator constants are not normalized operational state or projections |
| Capacity intelligence | HARDCODED/INFERRED | No explicit workload, staffing, station or throughput projection |
| Driver attribution | ABSENT | No model-derived or deterministic forecast attribution |
| Structured historical retrieval | UNUSED/ABSENT | Stored decisions/outcomes do not influence later decisions |
| Document RAG | ABSENT | Appropriate until a real corpus and retrieval benchmark exist |
| Manager approval | REAL for reactive path | Approve/reject/edit endpoint with idempotency and recommendation expiry exists |
| Outcome verification | BROKEN semantically | Limited post-window activity can be labeled improvement without forecast/actual comparison or causal design |
| Decision trace | PARTIAL | Reactive records exist, but there is no dossier/model/guard-to-outcome predictive trace |
| React frontend | REAL but mixed | Incident, action and outcome paths call REST APIs; dashboard/activity views include invented mock metrics |
| React mock intelligence | HARDCODED | Revenue, capacity, timing, outlet messages, shifts and service flow live in `src/data/mock.ts` |
| Backend HTML UI | HARDCODED/PLACEHOLDER | Separate scripted demo is served from backend `/`; it duplicates the React product surface |
| Predictive Today UI | ABSENT | No forecast-first SKU, stockout, capacity, driver or forecast-versus-actual experience |
| Forecast evaluation harness | ABSENT | No per-row forecast record or baseline/model comparison |
| Agent evaluation harness | ABSENT | No labelled dossiers, acceptable/forbidden actions, grounding or consistency metrics |

## Hardcoded or synthetic intelligence presented to users

- Fixture baseline order, cancellation, preparation, handoff and review values.
- Fixed operational-overload playbook and rationale.
- Template explanation wording.
- Scripted simulator deterioration and post-approval recovery.
- React dashboard revenue, capacity, timing, service-flow, manager-shift and outlet-message data.
- Standalone backend HTML demo behavior and display data.

These are acceptable only when visibly labelled demo fixtures. They must not be presented as predictive output.

## Disconnected and misleading boundaries

- The package baseline reports insufficient history correctly, but the backend overwrites that truth with fixture sufficiency.
- LangGraph narrates calculations already completed outside the graph.
- Persisted outcomes are not retrieved for later decisions.
- Simulator SKU selection does not become a canonical outlet × SKU demand dataset.
- The architecture describes comparable historical windows, while the executable query selects immediately preceding windows.
- Docker Compose and architecture identify `apps/frontend/` as canonical, but backend `/` independently serves `templates/index.html`.
- Several React dashboard components render mock intelligence alongside real incident APIs.

## Assets worth preserving

- Typed event ingestion and normal simulator API path.
- PostgreSQL/Redis/outbox boundaries.
- Deterministic metric aggregation and detectors as reactive/residual monitoring.
- Decimal-oriented pure intelligence package conventions.
- Manager approval, idempotency and WebSocket notification foundations.
- Typed LLM adapter and deterministic explanation fallback pattern.
- React application shell and API client, after mock intelligence is removed.
- Existing deterministic test suite.

## Required migration boundary

The reactive pipeline should coexist with predictive development. New predictive artifacts and APIs must be additive until forecast, risk, decision and outcome parity are verified. The existing detector model `Signal` remains a reactive anomaly contract; new observations use the distinct `NormalizedSignal` terminology established by ADR 0001.

The canonical product frontend is `apps/frontend/`. The standalone backend HTML UI should be removed only after useful presentation elements are migrated and the React build, backend integration and demo runbook pass.

## Files inspected

- `AGENTS.md`, `nextLossline.md`, `FINAL_IMPLEMENTATION_PLAN.md`, `docs/architecture.md`
- `apps/backend/src/main.py`, API, DB, ingestion, streaming and intelligence modules
- backend migrations and tests
- `packages/intelligence/src/lossline_intelligence/` and its tests
- simulator runner, scenario and tests
- React entry point, pages, API/types, hooks, components and mock data
- backend `templates/index.html`
- Dockerfiles, Docker Compose, Makefile and demo runbook

