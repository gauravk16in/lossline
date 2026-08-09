# LOSSLine

**LOSSLine predicts where restaurant operations will lose money before service begins — forecasts demand, surfaces root causes, recommends a bounded action, and evaluates the outcome after.**

It is not a dashboard that shows what already happened. It is a pre-service intelligence system that works through a full predictive cycle: feature engineering → demand forecasting → inventory and capacity projection → risk detection → driver attribution → a guarded LangGraph agent → deterministic safety checks → manager approval → outcome evaluation against actuals.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LightGBM-4.6-3DB33F?style=flat-square" alt="LightGBM" />
  <img src="https://img.shields.io/badge/LangGraph-1.2-FF4B4B?style=flat-square" alt="LangGraph" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 17" />
</p>

---

<p align="center">
  <img src="ui/overview-section.png" alt="LOSSLine Overview Dashboard" width="95%" />
</p>

---

## The Problem

Restaurant operations generate signals from many places simultaneously:

| Source | Signal |
|---|---|
| POS / Aggregator | order volumes, channel mix (dine-in, Swiggy, Zomato, takeaway) |
| Kitchen Display (KDS) | prep stage durations, handoff waits, station queue depth |
| Inventory | on-hand batch quantities, replenishment schedules, safety buffers |
| Calendar | weekday, service window, local holidays, corporate events |
| Weather | rainfall, temperature anomalies |
| Commercial | active promotions, discount percentages per SKU |
| History | prior fulfilled demand, baseline windows, past decisions |

Managers typically read these signals in isolation, after the fact. By the time cancellation rates spike or a prep station bottlenecks, the damage is done.

**Most dashboards answer: "What happened?"**

**LOSSLine answers: "What is likely to happen in the next service window — and what should I do about it right now?"**

---

## How It Works

```
  POS · KDS · Inventory · Weather · Promotions · Calendar
                        │
                        ▼
     Point-in-Time Feature Pipeline
       (leakage-free, fingerprinted snapshots)
                        │
                        ▼
    LightGBM Quantile Demand Forecast
         [lower | point estimate | upper]
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
  Inventory Projection        Capacity Projection
  (stockouts, safety buffer)  (station load, queue depth)
          └─────────────┬─────────────┘
                        │
                        ▼
          Risk Detection
          INVENTORY_SHORTAGE · CAPACITY_OVERLOAD · DELIVERY_OVERSELL
                        │
                        ▼
          Driver Attribution
          (feature contributions ranked by impact)
                        │
                        ▼
          Immutable Forecast Dossier
          (curated evidence bundle, no raw tables)
                        │
                        ▼
          LangGraph Investigation Workflow
            load_context → assess_confidence
              → [widen_context?] → explain → recommend → finalize
                        │
                        ▼
          Deterministic Safety Guards
          (one-directional: can clamp, restrict, reject — never expand)
                        │
                        ▼
          Manager Review  →  Approve / Modify / Reject
                        │
                        ▼
          Outcome Evaluation
          (matured actuals vs. prediction intervals, WAPE / Pinball)
```

The LangGraph workflow, the LLM explanation, and the guards are all strictly separated from the math. **The LLM writes prose. It calculates nothing.**

---

## Repository Layout

```
lossline/
├── packages/intelligence/            # Pure domain package — no DB, no HTTP
│   └── src/lossline_intelligence/
│       ├── signals/                  # NormalizedSignal contracts, registry
│       ├── features/                 # Feature registry, catalog (15 registered features),
│       │                             #   point-in-time snapshot builder, pipeline
│       ├── forecasts/                # LightGBM GBT model (train + infer) + rolling baseline
│       ├── inventory/                # Usable-supply engine, stockout projection
│       ├── capacity/                 # Station workload engine, utilization + risk tier
│       ├── attribution/              # Driver evidence, ranked feature contributions
│       ├── dossiers/                 # ForecastDossier assembler — immutable context bundle
│       ├── decisioning/              # DecisionCandidate contracts, guards, agent
│       ├── narratives/               # Grounded LLM explanation generator + fallback
│       ├── retrieval/                # Structured comparable-period retrieval + policy docs
│       ├── outcomes/                 # Predictive outcome ingestion
│       └── evaluation/               # Forecast metrics (WAPE, MAPE, RMSE, Pinball),
│                                     #   rolling evaluation, agent evaluation, acceptance gate
│
├── apps/backend/                     # FastAPI async service
│   └── src/
│       ├── api/                      # Versioned REST + WebSocket, Clerk / API-key auth
│       ├── db/                       # SQLAlchemy 2.0 async ORM, Alembic migrations
│       ├── ingestion/                # Event envelope validation, transactional outbox
│       ├── intelligence/             # Orchestration layer — LangGraph runner, persistence,
│       │                             #   predictive cycle, scheduler, outcome verification
│       └── realtime/                 # WebSocket manager for live dashboard hydration
│
├── apps/frontend/                    # React 19 + TypeScript + Vite
│   └── src/
│       ├── pages/                    # Overview · Forecasts · Risks · Decisions
│       └── components/               # Demand charts, risk heatmap, decision review panel
│
└── simulator/                        # Physics-based synthetic kitchen
    └── lossline_simulator/
        ├── causal_world.py           # Latent demand model, inventory censoring, capacity
        └── scenarios/                # NORMAL_WEEKDAY, RAIN_DELIVERY_SURGE, HOLIDAY_DEMAND_SURGE,
                                      #   PROMOTION_LIMITED_INVENTORY, WEAK_DEMAND_HIGH_INVENTORY, …
```

---

## Technical Detail

### Feature Pipeline

The feature registry contains 15 explicitly defined, versioned features across 7 signal categories:

| Category | Feature | Availability |
|---|---|---|
| Calendar | `context.weekday`, `context.service_window`, `context.is_holiday`, `context.local_event` | Future-known |
| Operations | `context.delivery_share`, `context.data_quality` | At prediction time |
| Weather | `weather.state`, `weather.rainfall_mm` | Forecast vintage |
| Commercial | `promotion.active`, `promotion.discount_pct` | Scheduled future |
| Inventory | `inventory.opening_quantity` | At prediction time |
| Capacity | `capacity.available_minutes` | At prediction time |
| Demand history | `demand.fulfilled_quantity.lag1` | Historical lag |
| SKU static | `sku.base_demand`, `sku.workload_minutes` | Catalog |

Every feature carries a leakage rationale, max staleness, and missing-value strategy. Each `FeatureSnapshot` is fingerprinted deterministically — identical inputs produce identical artifact IDs.

### Forecasting

**`forecasts/gbt.py`** — LightGBM with `objective=regression_l1` (MAE). Prediction intervals use an empirical-residual method labelled `empirical_residual_80.v1`; these are not calibrated probabilities and are labelled as such. A rolling-origin chronological split (last 20% of rows by time) is used for evaluation. Minimum 20 training rows required before the model is admitted; below that, the system falls back to the baseline.

**`forecasts/baseline.py`** — Matching-window rolling baseline for cold starts and sparse-data conditions.

**Censoring** — Stockout-affected observations are flagged and excluded from training targets to prevent systematic downward bias.

### Inventory & Capacity Projections

Inventory and capacity are computed independently from the same forecast grain.

- **Inventory:** opening quantity, replenishment, safety buffer, demand point/lower/upper → ending inventory range → stockout scenario estimate.
- **Capacity:** SKU workload minutes per station, available station-minutes (staffed) → utilization lower/point/upper → risk tier (`LOW / MEDIUM / HIGH / CRITICAL`).

### LangGraph Workflow (Reactive Detection Path)

The investigation workflow (`apps/backend/src/intelligence/langgraph_workflow.py`) orchestrates post-detection analysis for the M1 reactive incident path:

```
START
  └─ load_context
       └─ assess_confidence
            ├─ [confidence < 0.50, first attempt] → widen_context → reassess_confidence
            └─ explain → recommend → finalize → END
```

LangGraph coordinates state transitions and stage logging. It does not compute confidence, revenue risk, or recommendations — those arrive as inputs from the deterministic intelligence pipeline.

### Decisioning & Guards

The agent produces a `DecisionCandidate` which must pass `guard_decision()` before being persisted.

**Decision actions (actual enum values):**

```python
class DecisionAction(StrEnum):
    NO_ACTION          = "NO_ACTION"
    ABSTAIN            = "ABSTAIN"
    ADJUST_PREP_QUANTITY = "ADJUST_PREP_QUANTITY"
    REALLOCATE_STAFF   = "REALLOCATE_STAFF"
    PAUSE_DELIVERY_SKU = "PAUSE_DELIVERY_SKU"
```

**Guard dispositions:** `ACCEPT` | `RESTRICT` | `REJECT` | `ABSTAIN`

Guards enforce: policy membership, evidence grounding, quantity finiteness and non-negativity, minimum lead time, maximum prep quantity, approval requirements for high-impact actions. A guard that fires `RESTRICT` may clamp quantity downward. It may **never** expand quantity, urgency, autonomy, or financial exposure.

### Historical Retrieval

`retrieval/engine.py` performs structured retrieval of comparable past periods, filtered by `outlet_id × service_window × weekday`. Optional keyword-scored policy document retrieval is supported but gated behind `corpus_admitted=True` (disabled by default until a real corpus exists).

### Outcome & Forecast Evaluation

`evaluation/forecast.py` computes per-row metrics (`WAPE`, `MAPE`, `RMSE`, `Pinball Loss` at the configured quantile). An acceptance gate requires the GBT model to show ≥5% primary improvement over baseline without subgroup regression exceeding 10%. Censored rows are excluded from metric computation and flagged explicitly.

### Simulator

`causal_world.py` generates a seeded synthetic kitchen with latent demand, inventory censoring, and capacity effects as independent causal layers. Fulfilled sales can be censored by inventory stockouts; preparation time can change under capacity pressure. Neither feeds back into latent demand within a window.

Golden scenarios shipped: `NORMAL_WEEKDAY`, `FRIDAY_DINNER_SURGE`, `RAIN_DELIVERY_SURGE`, `HOLIDAY_DEMAND_SURGE`, `PROMOTION_LIMITED_INVENTORY`, `WEAK_DEMAND_HIGH_INVENTORY`, `MISSING_WEATHER`. The simulator submits canonical events to `POST /api/v1/events` — it never writes directly to PostgreSQL or Redis.

---

## Test Coverage

```bash
# Intelligence package — 498 tests, all passing
pytest packages/intelligence/tests/
```

Tests exist for: baseline, cancellation detector, capacity projection, confidence scoring, signal correlation, decision guards, delay review detector, driver attribution, feature registry, feature snapshots, forecast baseline, forecast dossier, GBT model, handoff delay detector, inventory projection, metric snapshot builder, normalized signals, operational decision agent, order volume detector, predictive explanations, predictive outcomes, prep time detector, recommendations, retrieval, revenue risk, signal model, signal registry.

Every detector test covers: below-threshold, at-threshold, above-threshold, sparse-data, and repeatability cases.

---

## User Interface

<p align="center">
  <img src="ui/risk.png" alt="Risk Heatmap and At-Risk SKU Table" width="95%" />
</p>

<p align="center">
  <img src="ui/decision.png" alt="Decision Review Panel" width="95%" />
</p>

Four pages: **Overview** (demand forecast chart, key metrics, priority decision panel, at-risk SKUs), **Forecasts** (per-SKU forecast table, driver breakdown, accuracy metrics), **Risks** (risk heatmap, severity cards, detail panel with evidence), **Decisions** (pending / approved / completed decision queue, approve-modify-reject workflow).

---

## Getting Started

### Option 1 — Docker Compose (full stack)

```bash
git clone https://github.com/gauravk16in/lossline.git
cd lossline
cp .env.example .env
# Edit .env: set POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, and API keys
docker compose up --build
```

| Service | URL |
|---|---|
| Operator Dashboard | http://localhost:3000 |
| FastAPI + Swagger | http://localhost:8000/docs |
| Health / Readiness | http://localhost:8000/ready |

Run the simulator against a live stack:

```bash
docker compose --profile demo up simulator
```

### Option 2 — Local development

```bash
# Python 3.12 required
python3.12 -m venv .venv && source .venv/bin/activate

pip install -e "packages/intelligence[dev]"
pip install -r apps/backend/requirements.txt

# Start backend
PYTHONPATH=apps/backend:packages/intelligence/src \
  uvicorn src.main:app --app-dir apps/backend --reload --port 8000

# Start frontend
cd apps/frontend && npm ci && npm run dev

# Seed demo data (SQLite or Postgres)
PYTHONPATH=apps/backend:packages/intelligence/src:simulator \
  python apps/backend/seed_dashboard_demo.py
```

### Running Tests

```bash
# Intelligence domain tests
pytest packages/intelligence/tests/

# Frontend type check + lint
cd apps/frontend && npm run typecheck && npm run lint
```

---

## API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/events` | Ingest key | Submit canonical POS/KDS event |
| `GET` | `/api/v1/predictive/outlets` | Manager key | List outlets |
| `GET` | `/api/v1/predictive/summary` | Manager key | Aggregate forecast + risk + revenue metrics |
| `GET` | `/api/v1/predictive/forecasts/today` | Manager key | Demand forecasts with prediction intervals |
| `GET` | `/api/v1/predictive/forecasts/hourly` | Manager key | Hourly breakdown |
| `GET` | `/api/v1/predictive/risks/today` | Manager key | Active risk candidates |
| `GET` | `/api/v1/predictive/decisions/today` | Manager key | Decision candidates (pending / approved / completed) |
| `POST` | `/api/v1/predictive/decisions/{id}/review` | Manager key | Approve, modify, or reject a decision |
| `GET` | `/api/v1/predictive/exposure` | Manager key | Revenue-at-risk breakdown |
| `WS` | `/ws/events` | Manager key | Realtime update stream |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Async PostgreSQL — `postgresql+asyncpg://...` |
| `DIRECT_DATABASE_URL` | Yes | Sync PostgreSQL for Alembic — `postgresql://...` |
| `REDIS_URL` | Docker only | Redis stream transport |
| `INGEST_API_KEY` | Yes | Bearer key for event ingestion |
| `MANAGER_API_KEY` | Yes | Bearer key for dashboard + decisions |
| `ADMIN_API_KEY` | Yes | Demo reset endpoint |
| `DEMO_MODE` | No | `true` enables scenario seeding and demo reset |
| `SERVERLESS_MODE` | No | `true` for Vercel — disables Redis, uses inline processing |
| `CLERK_ISSUER` | Production | Clerk authentication issuer URL |
| `CLERK_JWKS_URL` | Production | Clerk JWKS endpoint |
| `CREDENTIAL_PEPPER` | Production | Server-side pepper for credential hashing |
| `VITE_CLERK_PUBLISHABLE_KEY` | Production | Frontend Clerk key |
| `LLM_API_KEY` | Optional | Enables LLM narrative explanations |
| `LLM_MODEL` | Optional | Default: `gpt-4.1-mini` |

See [`.env.example`](.env.example) for the full reference.

---

## Design Constraints

These are not aspirations — they are enforced in the codebase and tested:

- **LLM computes nothing numeric.** All forecasts, risk tiers, confidence scores, revenue impacts, and recommendations are produced by deterministic Python code. The LLM receives a curated `ForecastDossier` and writes grounded prose. If the LLM call fails, a deterministic template is used instead.
- **Guards are one-directional.** A guard may clamp, restrict, require approval, or reject an agent decision. It may never increase quantity, expand autonomy, or reduce approval requirements.
- **Outlet isolation.** Every signal, snapshot, correlation, and decision is scoped to a single `outlet_id`. Cross-outlet correlation is deferred beyond MVP.
- **Idempotent delivery.** Events write to a transactional outbox before Redis. Duplicate delivery produces no duplicate signal or incident.
- **Deterministic artifacts.** Identical inputs and versions produce identical artifact fingerprints — forecasts, snapshots, and evaluations are reproducible.
- **Censoring awareness.** Stockout-affected demand observations are flagged and excluded from model training targets.
