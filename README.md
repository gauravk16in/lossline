<div align="center">

# 🍽️ LOSSLine

### *Predict. Explain. Decide. Verify.*

**LOSSLine predicts where restaurant operations will lose money before service begins.**<br/>
It forecasts demand, surfaces root causes, recommends a bounded action, and evaluates the outcome after.

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.6-00AA44?style=for-the-badge)](https://lightgbm.readthedocs.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-FF4B4B?style=for-the-badge)](https://langchain-ai.github.io/langgraph)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)

<br/>

</div>

---

<div align="center">
  <img src="ui/overview-section.png" alt="LOSSLine Overview Dashboard" width="95%" />
  <br/><sub><i>Overview dashboard — live demand forecast, at-risk SKUs, key drivers, and priority decision panel</i></sub>
</div>

---

## 🧠 Why LOSSLine

Most dashboards answer: **"What happened?"** — after cancellations spike, stations bottleneck, or ingredients stock out.

LOSSLine answers: **"What will happen next service window, why, and what should I do about it right now?"**

Restaurant operations generate simultaneous signals across many layers:

| 📡 Source | Signal |
|:---|:---|
| POS / Aggregators | Order volumes, channel mix — Dine-in, Swiggy, Zomato, Takeaway |
| KDS (Kitchen Display) | Prep stage durations, handoff waits, station queue depth |
| Inventory | On-hand quantities, replenishment schedules, safety buffers |
| Calendar | Weekday, service window, local holidays, corporate events |
| Weather | Rainfall, temperature anomalies |
| Commercial | Active promotions, per-SKU discount percentages |
| History | Prior fulfilled demand, baseline windows, past decisions |

LOSSLine connects all of them — **before** the service window opens.

---

## ⚙️ How It Works

```
  POS · KDS · Inventory · Weather · Promotions · Calendar
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │     Point-in-Time Feature Pipeline        │
   │   leakage-free · fingerprinted · versioned │
   └──────────────────────────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │     LightGBM Quantile Demand Forecast     │
   │      lower bound │ point │ upper bound    │
   └──────────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
   ┌─────────────────┐     ┌─────────────────────┐
   │ Inventory Engine │     │  Capacity Engine     │
   │ stockouts · buffer│    │ station load · queue │
   └─────────────────┘     └─────────────────────┘
          └─────────────┬─────────────┘
                        ▼
   ┌──────────────────────────────────────────┐
   │           Risk Candidates                 │
   │  INVENTORY_SHORTAGE · CAPACITY_OVERLOAD   │
   │          DELIVERY_OVERSELL                │
   └──────────────────────────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │          Driver Attribution               │
   │  feature contributions ranked by impact  │
   └──────────────────────────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │          Forecast Dossier                 │
   │  curated evidence bundle — immutable      │
   └──────────────────────────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │      LangGraph Investigation Workflow     │
   │  load → assess → [widen?] → explain       │
   │            → recommend → finalize         │
   └──────────────────────────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │      Deterministic Safety Guards          │
   │  can clamp · restrict · reject            │
   │  can NEVER expand scope or exposure       │
   └──────────────────────────────────────────┘
                        │
                        ▼
           Manager: Approve · Modify · Reject
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │          Outcome Evaluation               │
   │  actuals vs. forecast · WAPE · Pinball   │
   └──────────────────────────────────────────┘
```

> **Critical design rule:** The LangGraph agent and LLM write prose. They calculate nothing. All forecasts, risk tiers, confidence scores, and revenue impacts are produced by deterministic Python code. If the LLM call fails, a deterministic fallback template is used.

---

## 🖥️ Screenshots

<div align="center">
  <img src="ui/risk.png" alt="Risk Heatmap and At-Risk SKU Table" width="95%" />
  <br/><sub><i>Risk page — severity heatmap, at-risk SKU table, and inventory detail panel</i></sub>
</div>

<br/>

<div align="center">
  <img src="ui/decision.png" alt="Decision Review Panel" width="95%" />
  <br/><sub><i>Decisions page — approve, modify, or reject a guarded AI recommendation with full evidence</i></sub>
</div>

---

## 🗂️ Repository Layout

```
lossline/
├── packages/intelligence/          # Pure domain package — no DB, no HTTP
│   └── src/lossline_intelligence/
│       ├── signals/                # NormalizedSignal contracts, registry
│       ├── features/               # 15-feature registry, catalog, snapshot builder
│       ├── forecasts/              # LightGBM GBT model + rolling baseline
│       ├── inventory/              # Usable-supply engine, stockout projection
│       ├── capacity/               # Station workload, utilization, risk tier
│       ├── attribution/            # Driver evidence, ranked feature contributions
│       ├── dossiers/               # ForecastDossier assembler (immutable)
│       ├── decisioning/            # DecisionCandidate, guards, agent
│       ├── narratives/             # Grounded LLM explanation + deterministic fallback
│       ├── retrieval/              # Comparable-period retrieval + policy docs
│       ├── outcomes/               # Predictive outcome ingestion
│       └── evaluation/             # WAPE · MAPE · RMSE · Pinball, acceptance gate
│
├── apps/backend/                   # FastAPI async service
│   └── src/
│       ├── api/                    # Versioned REST + WebSocket, Clerk/API-key auth
│       ├── db/                     # SQLAlchemy 2.0 async ORM, Alembic migrations
│       ├── ingestion/              # Event validation, transactional outbox
│       ├── intelligence/           # LangGraph runner, predictive cycle, scheduler
│       └── realtime/               # WebSocket manager
│
├── apps/frontend/                  # React 19 + TypeScript + Vite
│   └── src/
│       ├── pages/                  # Overview · Forecasts · Risks · Decisions
│       └── components/             # Demand charts, risk heatmap, decision panel
│
└── simulator/                      # Physics-based synthetic kitchen
    └── lossline_simulator/
        ├── causal_world.py         # Latent demand, inventory censoring, capacity
        └── scenarios/              # 7 golden scenarios (RAIN_SURGE, PROMOTION, …)
```

---

## 🔬 Technical Detail

<details>
<summary><strong>📐 Feature Pipeline</strong></summary>
<br/>

The feature registry contains **15 explicitly defined, versioned features** across 7 signal categories. Every feature carries a leakage rationale, max staleness, and missing-value strategy.

| Category | Features | Availability |
|:---|:---|:---|
| 📅 Calendar | `context.weekday`, `context.service_window`, `context.is_holiday`, `context.local_event` | Future-known |
| 🏭 Operations | `context.delivery_share`, `context.data_quality` | At prediction time |
| 🌦️ Weather | `weather.state`, `weather.rainfall_mm` | Forecast vintage |
| 🎁 Commercial | `promotion.active`, `promotion.discount_pct` | Scheduled future |
| 📦 Inventory | `inventory.opening_quantity` | At prediction time |
| ⚡ Capacity | `capacity.available_minutes` | At prediction time |
| 📊 Demand History | `demand.fulfilled_quantity.lag1` | Historical lag |
| 🍛 SKU Static | `sku.base_demand`, `sku.workload_minutes` | Catalog |

Each `FeatureSnapshot` is **deterministically fingerprinted** — identical inputs produce identical artifact IDs.

</details>

<details>
<summary><strong>📈 Demand Forecasting</strong></summary>
<br/>

**GBT Model** (`forecasts/gbt.py`) — LightGBM with `objective=regression_l1` (MAE). Prediction intervals use an empirical-residual method labelled `empirical_residual_80.v1` — these are **not** calibrated probabilities and are labelled as such.

- Rolling-origin chronological split (last 20% of rows by time)
- Minimum 20 training rows required before the model is admitted
- Below threshold → automatic fallback to deterministic rolling baseline
- Stockout-censored observations are **flagged and excluded** from training targets to prevent systematic downward bias

**Acceptance gate** — GBT must show ≥5% primary improvement over baseline without subgroup regression exceeding 10%.

</details>

<details>
<summary><strong>🛡️ Decisioning & Guards</strong></summary>
<br/>

**Decision actions (actual enum values from source):**

```python
class DecisionAction(StrEnum):
    NO_ACTION            = "NO_ACTION"
    ABSTAIN              = "ABSTAIN"
    ADJUST_PREP_QUANTITY = "ADJUST_PREP_QUANTITY"
    REALLOCATE_STAFF     = "REALLOCATE_STAFF"
    PAUSE_DELIVERY_SKU   = "PAUSE_DELIVERY_SKU"
```

**Guard dispositions:** `ACCEPT` | `RESTRICT` | `REJECT` | `ABSTAIN`

Guards enforce: policy membership, evidence grounding, quantity finiteness and non-negativity, minimum lead time (15 min default), maximum prep quantity, approval requirements for high-impact actions (`REALLOCATE_STAFF`, `PAUSE_DELIVERY_SKU`).

> A guard that fires `RESTRICT` may clamp quantity downward. It may **never** expand quantity, urgency, autonomy, or financial exposure.

</details>

<details>
<summary><strong>🔄 LangGraph Workflow</strong></summary>
<br/>

The investigation workflow orchestrates post-detection analysis, coordinating stage logging and state transitions. It calculates **no business facts**.

```
START
  └─ load_context
       └─ assess_confidence
            ├─ [confidence < 0.50, first attempt]
            │    └─ widen_context → reassess_confidence → explain
            └─ [otherwise] → explain
                                └─ recommend → finalize → END
```

If the LLM explanation fails at any point, a deterministic template is substituted. The workflow records the `explanation_source` and `fallback_reason` in its state.

</details>

<details>
<summary><strong>🧪 Simulator Scenarios</strong></summary>
<br/>

The causal world generates latent demand, inventory censoring, and capacity effects as **independent causal layers**. The simulator submits canonical events to `POST /api/v1/events` — never writing directly to PostgreSQL or Redis.

| Scenario | Description |
|:---|:---|
| `NORMAL_WEEKDAY` | Baseline calibration run |
| `FRIDAY_DINNER_SURGE` | Weekend evening demand peak |
| `RAIN_DELIVERY_SURGE` | Precipitation-driven aggregator spike |
| `HOLIDAY_DEMAND_SURGE` | Public holiday volume increase |
| `PROMOTION_LIMITED_INVENTORY` | Discount-driven demand with constrained supply |
| `WEAK_DEMAND_HIGH_INVENTORY` | Surplus risk scenario |
| `MISSING_WEATHER` | Sparse-feature abstention case |

</details>

---

## ✅ Test Coverage

```bash
# 498 tests — all passing
pytest packages/intelligence/tests/
```

Tests cover: baselines · cancellation detector · capacity projection · confidence scoring · signal correlation · decision guards · delay review detector · driver attribution · feature registry · feature snapshots · GBT forecast model · handoff delay detector · inventory projection · metric snapshot builder · normalized signals · operational decision agent · order volume detector · predictive explanations · predictive outcomes · prep time detector · recommendations · retrieval · revenue risk · signal model · signal registry.

Every detector test covers: below-threshold, at-threshold, above-threshold, sparse-data, and repeatability cases.

---

## 🚀 Getting Started

### Option 1 — Docker Compose *(full stack)*

```bash
git clone https://github.com/gauravk16in/lossline.git
cd lossline
cp .env.example .env
# Edit .env — set POSTGRES credentials and API keys (see .env.example)
docker compose up --build
```

| 🌐 Service | URL |
|:---|:---|
| Operator Dashboard | http://localhost:3000 |
| FastAPI + Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/ready |

Run the synthetic lunch rush simulator:
```bash
docker compose --profile demo up simulator
```

### Option 2 — Local Development

```bash
# Python 3.12 required
python3.12 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e "packages/intelligence[dev]"
pip install -r apps/backend/requirements.txt

# Backend (with live reload)
PYTHONPATH=apps/backend:packages/intelligence/src \
  uvicorn src.main:app --app-dir apps/backend --reload --port 8000

# Frontend
cd apps/frontend && npm ci && npm run dev

# Seed demo data
PYTHONPATH=apps/backend:packages/intelligence/src:simulator \
  python apps/backend/seed_dashboard_demo.py
```

---

## 🔌 API Reference

| Method | Path | Description |
|:---:|:---|:---|
| `POST` | `/api/v1/events` | Submit a canonical POS/KDS event |
| `GET` | `/api/v1/predictive/summary` | Forecast + risk + revenue aggregate |
| `GET` | `/api/v1/predictive/forecasts/today` | Demand forecasts with prediction intervals |
| `GET` | `/api/v1/predictive/forecasts/hourly` | Hourly breakdown |
| `GET` | `/api/v1/predictive/risks/today` | Active risk candidates |
| `GET` | `/api/v1/predictive/decisions/today` | Decision queue (pending · approved · completed) |
| `POST` | `/api/v1/predictive/decisions/{id}/review` | Approve · modify · reject |
| `GET` | `/api/v1/predictive/exposure` | Revenue-at-risk breakdown |
| `WS` | `/ws/events` | Realtime update stream |

---

## 🔑 Environment Variables

<details>
<summary>Expand configuration reference</summary>
<br/>

| Variable | Required | Description |
|:---|:---:|:---|
| `DATABASE_URL` | ✅ | Async PostgreSQL — `postgresql+asyncpg://...` |
| `DIRECT_DATABASE_URL` | ✅ | Sync PostgreSQL for Alembic migrations |
| `REDIS_URL` | Docker | Redis stream transport |
| `INGEST_API_KEY` | ✅ | Bearer key for event ingestion |
| `MANAGER_API_KEY` | ✅ | Bearer key for dashboard + decisions |
| `ADMIN_API_KEY` | ✅ | Demo reset endpoint |
| `DEMO_MODE` | — | `true` enables scenario seeding |
| `SERVERLESS_MODE` | — | `true` for Vercel — disables Redis, uses inline processing |
| `CLERK_ISSUER` | Production | Clerk authentication issuer URL |
| `CLERK_JWKS_URL` | Production | Clerk JWKS endpoint |
| `CREDENTIAL_PEPPER` | Production | Server-side pepper for credential hashing |
| `VITE_CLERK_PUBLISHABLE_KEY` | Production | Frontend Clerk publishable key |
| `LLM_API_KEY` | Optional | Enables LLM narrative explanations |
| `LLM_MODEL` | Optional | Default: `gpt-4.1-mini` |

See [`.env.example`](.env.example) for the full reference with inline comments.

</details>

---

## 📐 Design Constraints

These are enforced in code and tested — not aspirational:

> 🔒 **LLM computes nothing numeric.** All forecasts, risk tiers, confidence scores, and revenue impacts are produced by deterministic Python. The LLM receives a curated `ForecastDossier` and writes grounded prose only.

> 🔒 **Guards are one-directional.** A guard may clamp, restrict, require approval, or reject. It may never increase quantity, expand autonomy, or reduce approval requirements.

> 🔒 **Outlet isolation.** Every signal, snapshot, correlation, and decision is scoped to a single `outlet_id`. Cross-outlet correlation is deferred beyond MVP.

> 🔒 **Idempotent delivery.** Events write to a transactional outbox before Redis. Duplicate delivery produces no duplicate signal or incident.

> 🔒 **Deterministic artifacts.** Identical inputs and versions produce identical artifact fingerprints — forecasts, snapshots, and evaluations are reproducible.

---

<div align="center">
  <sub>Built with deterministic intelligence · guarded AI decisions · closed-loop outcome verification</sub>
</div>
