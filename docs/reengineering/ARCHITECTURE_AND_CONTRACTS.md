# Predictive Architecture and Contract Boundaries

Status: accepted for C01

Date: 2026-08-09

## Product contract

LOSSLine predicts operational risk before a service window, explains evidence-backed drivers, proposes a constrained response, obtains approval when policy requires it, observes actual results, and evaluates the forecast and decision afterward.

The system preserves five distinct artifact classes:

1. **Facts** — observed source data, normalized observations, inventory, capacity and policy.
2. **Predictions** — versioned model outputs with an as-of time and evaluated uncertainty.
3. **Agent judgment** — a bounded selection among allowed operational responses.
4. **Guards** — deterministic validation and policy enforcement after agent submission.
5. **Outcomes** — matured actuals and evaluation results, never retroactively inserted into original inputs.

No artifact may silently cross these boundaries. An explanation is not evidence, an agent statement is not a forecast, a recommendation is not an executed action, and a post-action improvement is not proof of causation.

## Canonical grain and time

The predictive grain is:

```text
outlet_id × sku_id × named service_window
```

Named service windows are configured per outlet and interpreted in the outlet timezone. Persisted timestamps are timezone-aware UTC. Window intervals are half-open: `[start, end)`.

Every predictive read accepts `prediction_as_of`. A source value can enter the original feature snapshot only when its knowledge and ingestion times are no later than that instant. A value may describe a future effective period when its exact vintage was already known.

The initial demo uses a configured Asia/Kolkata outlet and `LUNCH` service window. The contract remains multi-outlet and supports additional named windows without adding enum values to core domain models.

## Demand and outcomes

`demand_quantity` means latent customer-requested SKU quantity. It is distinct from:

- ordered quantity;
- fulfilled quantity;
- cancelled or unfulfilled quantity;
- observed sales;
- inventory consumption.

Stockout-affected observations are censored. They must be flagged and may not silently serve as true-demand targets. C03 freezes the synthetic latent-demand mechanism; C04 freezes training-target construction.

## Target runtime

```text
Raw source events and snapshots
  → normalization
  → signal and feature registries
  → point-in-time feature snapshot
  → accepted baseline or forecast artifact
  → inventory projection
  → capacity projection
  → distinct risk candidates
  → structured driver evidence
  → structured history and optional policy retrieval
  → bounded OperationalDecisionAgent
  → submit_operational_decision
  → schema validation
  → deterministic one-directional guard
  → grounded explanation
  → durable manager review
  → actual-outcome ingestion
  → forecast, risk and decision evaluation
```

LangGraph orchestrates persisted artifacts and real transitions. It contains no forecast formulas, inventory arithmetic, capacity arithmetic, confidence arithmetic or policy limits.

## Ownership

### `packages/intelligence/`

Owns validated contracts, registries, point-in-time dataset construction, baselines, forecast adapters, evaluation, inventory/capacity projections, risk assessment, driver attribution, dossier construction, deterministic decision rules and guards. Domain algorithms are pure where practical.

### `apps/backend/src/intelligence/`

Owns repositories, transactions, artifact loading, schedulers, orchestration, LangGraph integration, checkpoint/resume, API mapping and persistence coordination. It calls package functions and does not duplicate their formulas.

### PostgreSQL and Redis

PostgreSQL is durable truth for source records, normalized observations, snapshots, forecasts, projections, decisions, approval actions, actuals, evaluations and traces. Redis transports work and transient notifications only.

### Simulator

The simulator generates a seeded causal world and calls normal ingestion APIs. It never writes directly to PostgreSQL or Redis and never fabricates model outputs.

### Frontend

`apps/frontend/` is the canonical UI. It renders backend facts and accepts manager input; it contains no business formulas. The backend HTML template is legacy and will be retired through C20 after useful presentation elements, if any, are migrated.

### LLM

The LLM may prioritize computed risks, select among allowed playbooks, request bounded evidence, and produce grounded prose. It may not calculate or alter demand, projections, risk values, driver contributions, confidence, revenue or outcomes.

## Core artifact contracts

The field lists below freeze responsibilities and identity boundaries. Detailed typed models are owned by their implementation chunks.

### `NormalizedSignal`

Registry-backed observed fact with `signal_id`, outlet/entity identity, `observed_at`, effective interval, source, category, type, typed value, unit, dimensions, quality and provenance. This is distinct from the existing reactive detector `Signal`.

### `FeatureSnapshot`

Immutable point-in-time model input containing snapshot ID/version, prediction as-of, grain, target window, registry version, typed feature values, source signal IDs, missing/imputed flags, and a deterministic fingerprint.

### `ForecastResult`

Contains forecast ID, grain, prediction as-of, target window, point/lower/upper demand, interval method, model or baseline version, feature snapshot ID, data sufficiency, quality flags and creation time. It never contains agent-authored values.

### `InventoryProjection`

Contains forecast reference, usable supply inputs, replenishment, safety buffer, lower/point/upper ending inventory, shortage/surplus scenarios, stockout-window estimate where supportable, unit, rule version and evidence IDs.

### `CapacityProjection`

Contains forecast reference, SKU workload inputs, available station/staff capacity, lower/point/upper utilization, queue context, risk tier, rule version and evidence IDs. It remains separate from inventory risk.

### `RiskCandidate`

Contains risk ID/type, grain, forecast/projection references, severity or tier, time-to-impact, structured evidence IDs, data quality and rule version. Inventory shortage, surplus, capacity overload and delivery oversell are distinct risk types.

### `DriverEvidence`

Contains driver ID, forecast reference, registered feature ID, rank, direction, method, evidence reference and optional numeric contribution only when the method supports it. It never asserts causality.

### `ForecastDossier`

Contains an immutable dossier ID/version and references or curated summaries for outlet/window, forecasts, inventory/capacity state and projections, risks, drivers, historical performance, similar periods, previous decisions, constraints, policy references, data quality and provenance. Raw tables, raw event streams and provider payloads are prohibited.

### `DecisionCandidate`

Contains decision ID/version, dossier and forecast references, outlet/window, risk type, optional SKU, allowed action enum, optional quantity/unit, execute-by time, reason code, evidence IDs, urgency, action risk, approval requirement and constraints considered. `NO_ACTION` and `ABSTAIN` are first-class results.

### `GuardResult`

Contains guard-result ID/version, submitted and final decision references, validity, violations, restrictions, approval correction, unsupported claims and terminal disposition. Guards can accept, restrict, reject or abstain; they cannot expand action scope.

### `DecisionTrace`

Links dossier, snapshot, forecast/model, projections, risks, drivers, retrieval, agent submission, guard result, explanation, manager action, execution record, actual outcome and evaluation artifacts with timestamps and versions.

### `ActualOutcome`

Contains the identical forecast grain/window, matured actual demand, fulfilled/unfulfilled quantity, inventory and capacity outcomes, censoring/missing status, source IDs and maturity time. It does not contain causal claims.

## Identity and version rules

- `outlet_id` is canonical; new predictive code never introduces `restaurant_id`.
- IDs are deterministic where inputs and versions fully determine an artifact; otherwise they are persisted once and immutable.
- Every calculation stores its algorithm/model version.
- Every model artifact stores training cutoff, dataset fingerprint, feature-registry version, code version, parameters, evaluation metrics and checksum.
- Re-running an identical deterministic input/version produces an identical artifact fingerprint.
- Output artifacts reference inputs by ID; mutable nested copies are not sources of truth.

## Forecast uncertainty and decision support

LOSSLine does not expose one magic confidence number. It keeps separate:

- forecast lower/point/upper range;
- historical model accuracy and bias;
- input data quality;
- deterministic operational risk;
- qualitative decision-support strength;
- action risk.

Numeric decision confidence is prohibited until labelled calibration supports it. Initial user-facing decision support uses `LOW`, `MEDIUM` or `HIGH` with its basis available for inspection.

## Agent and tool boundary

One `OperationalDecisionAgent` is the default. Additional agents require evidence that a separately evaluated responsibility cannot be handled by deterministic code or bounded tools.

The agent receives a `ForecastDossier`, not raw data. Read tools return typed persisted artifacts. Tool count and repair count are bounded. The only terminal proposal path is `submit_operational_decision`; free-form completion cannot become a decision.

## Guard boundary

After strict schema validation, deterministic guards verify:

- artifact, outlet, SKU and window references;
- evidence membership and numeric grounding;
- action enum and policy eligibility;
- quantity finiteness, non-negativity, units and rounding;
- lead-time, execute-by, capacity, inventory and safety limits;
- approval policy;
- unsupported numeric or causal claims.

The guard is one-directional. It may reduce quantity/scope, require approval, reject or abstain. It may never increase quantity, urgency, autonomy, customer impact or financial exposure.

## Retrieval boundary

Structured PostgreSQL retrieval is first for comparable periods, forecasts, decisions and outcomes. Document retrieval is limited to SOPs, policies, supplier terms, manager notes and narrative summaries. Retrieved text cannot overwrite computed artifacts. A vector database requires a real corpus and measured retrieval benefit.

## Evaluation boundary

Forecast evaluation, agent evaluation and outcome verification are separate:

- forecast evaluation compares baseline/model predictions with matured actuals;
- risk evaluation measures stockout, surplus and overload classifications;
- agent evaluation uses labelled dossiers and acceptable/forbidden decisions;
- guard evaluation measures valid acceptance and unsafe rejection;
- explanation evaluation measures grounding and unsupported claims;
- outcome evaluation records association after manager action without causal overclaiming.

Gold decisions and matured actuals do not enter live dossier construction.

## Reactive coexistence

The existing incident pipeline remains operational while predictive artifacts are introduced additively. Reactive detectors later serve real-time condition monitoring and forecast-residual evidence. They are not renamed or silently repurposed.

Retiring a reactive component requires contract parity, migration/replay evidence, passing integration and demo tests, and an accepted decision record. No big-bang replacement is permitted.

## Deferred decisions owned by later chunks

- C03: synthetic causal assumptions and scenario parameters.
- C04: target construction and detailed feature definitions.
- C05: baseline hierarchy and minimum history.
- C06: exact boosted-tree library and artifact format.
- C07: acceptance metric thresholds and interval calibration gate.
- C08: safety-buffer, replenishment and stockout-curve formulas.
- C09: workload, station and effective-capacity formulas.
- C10: attribution method and wording limits.
- C12–C14: exact tools, action enums, quantity bounds and repair policy.
- C15: retrieval scoring and document-corpus admission.
- C16: checkpoint implementation.
- C18: labelled agent metrics and acceptance thresholds.
- C21: outcome maturity and missing/censored rules.

