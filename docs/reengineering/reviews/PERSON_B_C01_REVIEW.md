# Person B — C01 Architecture and Contracts Review

Reviewer: Person B (Product/Platform)

Review date: 2026-08-09

Status: ACCEPTED with migration concerns noted

## Scope

This review covers [ARCHITECTURE_AND_CONTRACTS.md](file:///c:/Users/chand/lossline/docs/reengineering/ARCHITECTURE_AND_CONTRACTS.md) and [C01_ARCHITECTURE_AND_CONTRACTS.md](file:///c:/Users/chand/lossline/docs/reengineering/chunks/C01_ARCHITECTURE_AND_CONTRACTS.md) from the perspective of backend persistence, API design, orchestration and frontend integration.

## Accepted contract understanding

### Artifact boundaries

Person B confirms understanding of all 12 core artifact contracts. Each produces a distinct persistence responsibility:

| Artifact | Backend persistence responsibility | Current state |
|---|---|---|
| `NormalizedSignal` | New table with registry-validated schema | No table — reactive `signals` table is semantically different |
| `FeatureSnapshot` | Immutable versioned row with deterministic fingerprint | No table |
| `ForecastResult` | Immutable row keyed by grain, as-of and model version | No table |
| `InventoryProjection` | References forecast; stores supply/demand scenarios | No table |
| `CapacityProjection` | References forecast; stores utilization/risk | No table |
| `RiskCandidate` | References forecast and projection; typed risk | No table — reactive `incidents` table has semantic overlap but different identity |
| `DriverEvidence` | References forecast and feature; ranked attribution | No table |
| `ForecastDossier` | Immutable assembly of references; no raw data | No table |
| `DecisionCandidate` | References dossier; constrained action | No table — reactive `recommendations` + `actions` are structurally different |
| `GuardResult` | One-directional post-submission validation | No table |
| `DecisionTrace` | Full provenance chain from dossier to outcome | No table — reactive `incidents` carry partial trace |
| `ActualOutcome` | Matured actuals at forecast grain | `outcomes` table exists but stores reactive status, not forecast-vs-actual comparison |

### Ownership boundaries

Person B acknowledges:

- `packages/intelligence/` owns all deterministic domain logic, models and registries. Person B imports these — never duplicates formulas.
- `apps/backend/src/intelligence/` owns repositories, transactions, artifact loading, schedulers, orchestration, LangGraph integration, checkpoint/resume, API mapping and persistence coordination.
- PostgreSQL is durable truth; Redis is transport only.
- The LLM never calculates metrics, confidence, revenue, recommendations or outcomes.

### Grain and time

- Canonical grain: `outlet_id × sku_id × named service_window`.
- Timestamps are timezone-aware UTC.
- `prediction_as_of` controls temporal visibility.
- Windows are half-open `[start, end)`.
- Named service windows are configured per outlet in outlet timezone.

Person B notes: the current [windows.py](file:///c:/Users/chand/lossline/apps/backend/src/intelligence/windows.py) uses UTC-epoch-aligned 30-minute windows, which is incompatible with named service windows. Migration path: C04 introduces service window configuration; the reactive path continues using UTC windows until retirement.

## Migration concerns

### 1. `restaurant_id` → `outlet_id`

**Scope**: Every DB table, SQLAlchemy model, API endpoint, and ingestion schema currently uses `restaurant_id`. The architecture freezes `outlet_id` as canonical.

**Current files affected**:
- [db/models.py](file:///c:/Users/chand/lossline/apps/backend/src/db/models.py) — `Restaurant`, `Event`, `MetricWindow`, `Signal`, `Incident` tables
- [api/endpoints.py](file:///c:/Users/chand/lossline/apps/backend/src/api/endpoints.py) — `restaurant_id` in event ingestion, auto-provisioning, incident queries
- [intelligence/persistence.py](file:///c:/Users/chand/lossline/apps/backend/src/intelligence/persistence.py) — `restaurant_id` in all queries
- [config.py](file:///c:/Users/chand/lossline/apps/backend/src/config.py) — no direct reference, but fixture defaults reference outlets
- Ingestion schemas — `restaurant_id` field in `EventEnvelope`

**Resolution**: New predictive tables use `outlet_id` from day one. The existing reactive tables keep `restaurant_id` during coexistence. A view or alias layer bridges them. Full rename happens in C19 if the reactive path is retired first.

### 2. Reactive `Signal` table vs `NormalizedSignal`

The existing [Signal model](file:///c:/Users/chand/lossline/apps/backend/src/db/models.py#L115-L144) stores reactive detector output: severity (float), current/baseline value, deviation, and a window. The C01 `NormalizedSignal` is a registry-validated observation with typed values, quality, provenance, effective intervals, entity identity and dimensions.

These are distinct tables. Person B will create a new `normalized_signals` table for predictive use. The reactive `signals` table remains untouched.

### 3. LangGraph placeholder → durable orchestration

The current [langgraph_workflow.py](file:///c:/Users/chand/lossline/apps/backend/src/intelligence/langgraph_workflow.py) narrates calculations already completed before graph entry. C01 mandates that LangGraph nodes compute, retrieve, validate, persist or manage real transitions with durable review checkpoints.

**Resolution**: C16 replaces the placeholder graph. Until then the reactive graph continues operating.

### 4. Backend HTML at `/`

The [serve_ui](file:///c:/Users/chand/lossline/apps/backend/src/main.py#L97-L106) endpoint serves `templates/index.html`. C01 accepts React as canonical and gates HTML retirement to C20.

**Resolution**: No changes now. Person B will compare HTML and React features during C20 before removing.

### 5. Frontend mock data

[mock.ts](file:///c:/Users/chand/lossline/apps/frontend/src/data/mock.ts) contains hardcoded revenue, capacity, timing, incident, shift, service-flow and chain-metric data. [types/index.ts](file:///c:/Users/chand/lossline/apps/frontend/src/types/index.ts) mirrors reactive Python models only.

**Resolution**: C20 replaces mock data with API calls to frozen backend schemas. New predictive types (`ForecastResult`, `InventoryProjection`, etc.) are added to frontend only after backend API schemas are frozen (C19).

## Deferred decisions acknowledged

| Decision | Owner chunk | Person B impact |
|---|---|---|
| Baseline hierarchy and minimum history | C05 | API may expose baseline comparison |
| Exact model library and artifact format | C06 | Artifact storage format affects DB schema |
| Safety-buffer, replenishment formulas | C08 | Person B implements C08 domain logic in `packages/intelligence/` |
| Workload, station, capacity formulas | C09 | Person B implements C09 domain logic in `packages/intelligence/` |
| Checkpoint implementation | C16 | Person B owns C16 LangGraph |
| Backend API schemas | C19 | Person B owns C19 |
| Frontend migration gate | C20 | Person B owns C20 |

## Conclusion

C01 contracts are accepted. All 12 artifact boundaries, the ownership model, grain/time semantics, and agent/guard/evaluation separation are understood. Migration concerns are documented and assigned to their owning chunks. No competing models, registries or formulas will be created.
