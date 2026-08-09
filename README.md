# LOSSLine

**Predictive operational intelligence for multi-outlet restaurants — forecasting demand and operational risks before service peaks, explaining the root causes, recommending constrained actions, and evaluating actual outcomes.**

LOSSLine moves restaurant operational decisions from reactive post-mortems to pre-service prevention. By fusing point-of-sale events, kitchen prep stages, inventory levels, channel mix, promotions, and contextual factors (weather, day-of-week, rush patterns), LOSSLine forecasts latent demand, projects inventory shortages and kitchen station bottlenecks, attributes driving factors using SHAP, proposes bounded operational interventions through a guarded AI decision agent, and closes the loop by evaluating forecast accuracy and decision efficacy against matured actuals.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LightGBM-4.6-00ADFF?style=flat-square&logo=scikitlearn&logoColor=white" alt="LightGBM" />
  <img src="https://img.shields.io/badge/LangGraph-1.2-FF4B4B?style=flat-square&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/PostgreSQL-17.6-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

---

## Overview

<p align="center">
  <img src="ui/overview-section.png" alt="LOSSLine Dashboard Overview" width="95%" />
</p>

---

## The Problem

High-volume restaurant and cloud kitchen operations generate continuous operational signals:

* Point-of-Sale (POS) order rushes and channel mix changes (Dine-in vs. Swiggy/Zomato/Aggregators)
* Kitchen Display System (KDS) prep stage timings, station queues, and handoff delays
* Ingredient batch prep, safety buffers, and shelf-life expiration
* Contextual dynamics including sudden weather shifts, local holidays, and active discount campaigns

Traditional operational dashboards only answer **"What happened?"** after the rush is over — when orders are already cancelled, prep stations are bottlenecked, ingredients have stocked out, and customer reviews have degraded.

**LOSSLine answers:**
> *"What is likely to happen during the upcoming service window, why is it going to happen, what specific action should be taken right now to prevent loss, and how effective was that intervention after the rush?"*

---

## How LOSSLine Works

LOSSLine executes a continuous, closed-loop predictive cycle that strictly separates deterministic mathematical computations from generative language explanations:

```text
  Operational & Contextual Signals (POS, KDS, Stock, Weather, Promos)
                                 │
                                 ▼
         Point-in-Time Feature Pipeline (Leakage-Free Snapshots)
                                 │
                                 ▼
      Multi-Horizon Demand Forecast (Quantile GBT / LightGBM)
                    [Lower 5% | Point Estimate | Upper 95%]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       Inventory Projection             Capacity Projection
     (Stockouts, Spoilage, Shelf-life)   (Station Bottlenecks, Queues)
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                     Operational Risk Detection
          (INVENTORY_SHORTAGE, CAPACITY_OVERLOAD, DELIVERY_OVERSELL)
                                 │
                                 ▼
             Driver Attribution Engine (TreeSHAP & Gradient)
                                 │
                                 ▼
                    Immutable Forecast Dossier
                                 │
                                 ▼
         Operational Decision Agent (LangGraph Workflow)
            - Queries Historical Analogous Windows
            - Selects Constrained Operational Playbook
                                 │
                                 ▼
          Deterministic Safety Guards (One-Directional Bounds)
            - Enforces Safety Stock, Lead Times, Station Limits
            - Mandates Human Approval for Financial Impact
                                 │
                                 ▼
          Manager Review Dashboard (Approve / Modify / Reject)
                                 │
                                 ▼
          Closed-Loop Outcome Evaluation & Model Calibration
            - Matured Actual Demand vs. Prediction Intervals
            - Decision Value Realization & Residual Tracking
```

---

## Core System Architecture

LOSSLine is designed as a modular monolith with strict domain and data-ownership boundaries:

```text
lossline/
├── packages/intelligence/        # Pure domain intelligence (Zero DB/Network coupling)
│   └── src/lossline_intelligence/
│       ├── signals/             # Normalized signal contracts & registries
│       ├── features/            # 50+ feature transforms & point-in-time snapshots
│       ├── forecasts/           # Baseline & LightGBM Quantile GBT demand models
│       ├── inventory/           # Usable stock, replenishment & stockout projection
│       ├── capacity/            # Prep station load, queue depth & bottleneck engine
│       ├── attribution/         # TreeSHAP driver importance & feature impact
│       ├── dossiers/            # Immutable structured context assemblers
│       ├── decisioning/         # Operational playbooks, agents & deterministic guards
│       ├── narratives/          # Grounded LLM explanations citing verified evidence
│       └── outcomes/            # Actuals ingestion, WAPE/MAPE/Pinball evaluation
│
├── apps/backend/                # FastAPI serverless & async service
│   ├── src/
│   │   ├── api/                 # Versioned REST endpoints & Clerk/API Key auth
│   │   ├── db/                  # SQLAlchemy 2.0 async models & Alembic migrations
│   │   ├── ingestion/           # POS/KDS event validation & transactional outbox
│   │   ├── intelligence/        # Orchestration, persistence mapper & LangGraph runner
│   │   └── realtime/            # WebSocket feeds for live dashboard hydration
│   └── migrate.py               # Database migration & schema bootstrap
│
├── apps/frontend/               # React 19 + TypeScript + Vite dashboard
│   └── src/
│       ├── pages/               # Overview, Forecasts, Risks, and Decisions views
│       ├── components/          # Recharts visualizations, heatmaps & action panels
│       └── state/               # Unified dashboard state & API client
│
└── simulator/                   # Physics-based multi-outlet synthetic environment
    └── lossline_simulator/
        ├── causal_world.py      # Kitchen physics, queueing theory & order arrival
        └── scenarios/           # Repeatable lunch rush & disruption scenarios
```

---

## Technical Highlights

### 1. Point-in-Time Feature Pipeline
* **Leakage-Free Snapshots:** Guarantees that feature calculation for any `prediction_as_of` timestamp only incorporates data ingested strictly prior to that instant.
* **50+ Engineered Signals:** Lags, rolling window medians, hour/day-of-week cyclical encodings, weather shocks (precipitation, temperature anomalies), active promotional discounts, channel distribution ratios, and historic station prep duration p90s.
* **Immutable Fingerprinting:** Each `FeatureSnapshot` is hashed deterministically to guarantee reproducible model inference.

### 2. Multi-Horizon Probabilistic Forecasting
* **Quantile GBT Models:** Powered by LightGBM, predicting point demand along with 10th and 90th percentile prediction intervals to model operational volatility.
* **Fallback Baselines:** Deterministic matching-window rolling baselines with exponential smoothing ensure continuous operation even during sparse-data cold starts.
* **Censored Demand Correction:** Automatically flags and accounts for stockout-censored historical periods to prevent downward bias in future forecasts.

### 3. Disentangled Inventory & Station Capacity Projections
* **Inventory Projections:** Computes batch sizes, on-hand counts, scheduled in-transit deliveries, safety buffers, and spoilage curves to identify SKU-level stockout timestamps.
* **Capacity Projections:** Evaluates station-by-station workload (fryer, grill, assembly, packing) against staffed labor capacity to predict bottleneck queues before orders accumulate.

### 4. Explainable Driver Attribution (SHAP)
* Converts complex ensemble predictions into clear, ranked, and quantifiable feature contributions.
* Distinguishes seasonal drift, weather surges, aggregator promotions, and base run-rates so operators understand *why* demand is shifting.

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Top Forecast Drivers (Lunch Window · Meghana Indiranagar)              │
├────────────────────────────────┬───────────────┬───────────────────────┤
│ Driver Feature                 │ Impact (Units)│ Relative Contribution │
├────────────────────────────────┼───────────────┼───────────────────────┤
│ Rain Spike (Precipitation)     │ +18.4 portions│ ████████████ 38%      │
│ 20% Aggregator Campaign        │ +12.1 portions│ ████████ 25%          │
│ Historical Friday Lunch Trend  │  +9.8 portions│ ██████ 20%            │
│ Local Corporate Holiday        │  -4.2 portions│ ███ 9%                │
└────────────────────────────────┴───────────────┴───────────────────────┘
```

### 5. Guarded Decision Agent & LangGraph Workflow
* **Bounded Tool Execution:** The `OperationalDecisionAgent` operates against a curated `ForecastDossier`.
* **Standardized Playbooks:** Selects from strictly typed operational responses:
  * `PREP_BATCH_ADVANCE` (Initiate batch prep 45 mins early)
  * `INVENTORY_REORDER` (Trigger emergency supplier replenishment)
  * `CHANNEL_THROTTLE` (Throttle aggregator radius / pause select items)
  * `STATION_REBALANCE` (Reallocate kitchen staff to bottleneck station)
  * `NO_ACTION` / `ABSTAIN` (Explicit non-intervention when risk is within tolerance)
* **One-Directional Deterministic Guards:** Validates all agent submissions against physical constraints (maximum batch sizes, lead times, safety buffers). Guards can clamp, restrict, require approval, or reject — but can *never* expand scope or financial exposure.
* **Grounded Narratives:** LLM synthesizes concise managerial summaries strictly referencing verified artifacts; numeric computations are never delegated to the LLM.

### 6. Closed-Loop Outcome Verification
* Automatically ingests matured actuals after service windows close.
* Tracks forecast performance across **WAPE**, **MAPE**, **RMSE**, and **Pinball Loss**.
* Evaluates decision effectiveness by comparing observed stockouts, prep times, and revenues against the counterfactual projection.

---

## User Interface

<p align="center">
  <img src="ui/risk.png" alt="Operational Risk Heatmap and Inventory Tracking" width="95%" />
</p>

<p align="center">
  <img src="ui/decision.png" alt="Guarded Operational Decision Review" width="95%" />
</p>

---

## Getting Started

### Prerequisites

* **Python 3.12+**
* **Node.js 18+** & **npm**
* **Docker & Docker Compose** (Optional, for containerized deployment)

---

### Option 1: Quickstart with Docker Compose

Run the entire platform (PostgreSQL 17, Redis 8, FastAPI Backend, React Frontend, and Simulator) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/gauravk16in/lossline.git
cd lossline

# 2. Copy the environment configuration
cp .env.example .env

# 3. Start all services
docker compose up --build
```

Access the interfaces:
* **Operator Dashboard:** [http://localhost:3000](http://localhost:3000)
* **FastAPI Backend & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Backend Health Check:** [http://localhost:8000/ready](http://localhost:8000/ready)

---

### Option 2: Local Developer Setup

#### 1. Setup Backend & Intelligence Engine

```bash
# Create and activate a Python 3.12 virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install intelligence package in editable mode with dev dependencies
pip install -e "packages/intelligence[dev]"

# Install backend dependencies
pip install -r apps/backend/requirements.txt

# Run database migrations
PYTHONPATH=apps/backend:packages/intelligence/src python apps/backend/migrate.py
```

#### 2. Start the Backend API

```bash
# Run FastAPI with live reload
PYTHONPATH=apps/backend:packages/intelligence/src uvicorn src.main:app --app-dir apps/backend --reload --port 8000
```

#### 3. Setup and Run the Frontend

```bash
cd apps/frontend
npm ci
npm run dev
```

The frontend will start at `http://localhost:5173` (or `http://localhost:3000` depending on port availability).

#### 4. Seed Interactive Demo Data

To populate the database with a multi-outlet lunch rush simulation:

```bash
PYTHONPATH=apps/backend:packages/intelligence/src:simulator python apps/backend/seed_dashboard_demo.py
```

---

## Testing & Quality Assurance

LOSSLine enforces comprehensive testing across domain models, ML estimators, deterministic guards, and REST workflows.

```bash
# Run all intelligence domain tests (490+ unit and property tests)
pytest packages/intelligence/tests/

# Run backend API and persistence integration tests
PYTHONPATH=apps/backend:packages/intelligence/src pytest apps/backend/tests/

# Run frontend typechecking and linting
cd apps/frontend
npm run typecheck
npm run lint
```

---

## API Surface

The FastAPI backend exposes versioned, typed REST endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness check (validates DB connection) |
| `POST` | `/api/v1/events` | Ingests canonical POS/KDS operational events |
| `GET` | `/api/v1/predictive/outlets` | Lists configured outlets and metadata |
| `GET` | `/api/v1/predictive/summary` | Retrieves aggregate forecast, risk, and revenue metrics |
| `GET` | `/api/v1/predictive/forecasts/today` | Returns point-in-time demand forecasts and prediction intervals |
| `GET` | `/api/v1/predictive/risks/today` | Fetches active inventory and capacity risk candidates |
| `GET` | `/api/v1/predictive/decisions/today` | Retrieves guarded decision candidates and manager action items |
| `POST` | `/api/v1/predictive/decisions/{id}/review` | Records manager decision approval, modification, or rejection |
| `GET` | `/api/v1/predictive/exposure` | Returns quantified revenue-at-risk breakdown by outlet |
| `WS` | `/ws/events` | Realtime stream for live dashboard state updates |

---

## Environment Configuration

| Variable | Description | Default / Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://lossline:lossline_demo@localhost:5432/lossline` |
| `DIRECT_DATABASE_URL` | Direct PostgreSQL connection for Alembic migrations | `postgresql://lossline:lossline_demo@localhost:5432/lossline` |
| `REDIS_URL` | Redis connection URL for outbox stream delivery | `redis://localhost:6379/0` |
| `DEMO_MODE` | Enables synthetic demo reset and scenario seeding | `true` |
| `SERVERLESS_MODE` | Optimizes runtime for Vercel Python serverless | `false` |
| `INGEST_API_KEY` | Secret key for POS/KDS event ingestion endpoints | `demo-key` |
| `MANAGER_API_KEY` | Secret key for manager action endpoints | `demo-key` |
| `CLERK_ISSUER` | (Production) Clerk authentication issuer URL | `https://clerk.your-domain.com` |
| `CLERK_JWKS_URL` | (Production) Clerk JWKS public key endpoint | `https://clerk.your-domain.com/.well-known/jwks.json` |
| `VITE_CLERK_PUBLISHABLE_KEY` | (Production) Clerk publishable key for React UI | `pk_test_...` |
| `LLM_API_KEY` | Optional API key for LLM narrative explanations | `sk-...` |
| `LLM_MODEL` | LLM model identifier | `gpt-4o-mini` |

---

## Core Architectural Guarantees

1. **Deterministic Numbers, Grounded Prose:** Machine learning estimators and mathematical formulas compute all forecasts, risk tiers, confidence scores, and revenue impacts. The LLM is restricted to phrasing grounded managerial explanations from verified dossiers.
2. **One-Directional Safety Guards:** AI agent recommendations must pass through deterministic policy guards. Guards can clamp quantities, increase review requirements, or reject actions, but can never escalate risk or autonomy.
3. **Multi-Tenant Outlet Isolation:** All temporal correlations, feature aggregations, and decision traces are scoped strictly to unique `outlet_id` boundaries.
4. **Idempotent Outbox Processing:** Ingested events are recorded in a transactional outbox table alongside canonical entity state to guarantee at-least-once, zero-loss stream processing.
5. **Traceability:** Every decision candidate maintains a verifiable trace linking back to its `ForecastDossier`, `FeatureSnapshot`, model versions, and underlying POS/KDS source events.
