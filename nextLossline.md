• # A. Current Architecture Diagnosis

  The executable product is a functioning reactive anomaly-and-incident demo. It is not yet a predictive operational intelligence system.

  Current executable flow:

  Synthetic simulator
    → POST /events
    → PostgreSQL event persistence / Redis stream
    → 30-minute event-window aggregation
    → historical/fixture baseline
    → five threshold detectors
    → overload correlation
    → deterministic confidence and fixed playbook
    → LangGraph stage orchestration
    → template or LLM explanation
    → manager approval
    → synthetic recovery events
    → coarse outcome classification
    → incident-oriented frontend

  Component classification:

   Component                           Classification                        Finding
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Event ingestion and validation      REAL                                  Typed events are accepted, persisted, streamed, and deduplicated.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Redis/outbox path                   REAL                                  Implements the intended asynchronous handoff, although much test coverage uses a
                                                                             mock Redis implementation.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Metric aggregation                  REAL                                  Order count, cancellation rate, preparation time, handoff time, and review metrics
                                                                             are computed from events.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Historical anomaly baseline         SYNTHETIC BUT COMPUTED / HARDCODED    Median/MAD code is real, but backend history selects immediately preceding 30-
                                                                             minute windows—not comparable weekday/service windows—and missing metrics are
                                                                             filled with fixture constants.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Sparse-history handling             BROKEN                                merge_baseline_with_fixture() forces sufficient_history=True, concealing
                                                                             insufficient evidence.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Detectors                           REAL                                  Five deterministic threshold detectors calculate deviations and emit reproducible
                                                                             signals.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Correlation                         REAL but narrow                       Requires order-volume, preparation-time, and cancellation spikes; produces only
                                                                             operational-overload candidates.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Confidence                          SYNTHETIC BUT COMPUTED                Computed deterministically from configured weights and evidence, but it is anomaly
                                                                             confidence—not calibrated forecast confidence.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Revenue-at-risk projection          SYNTHETIC BUT COMPUTED                Extrapolates the current order rate and excess cancellation rate for 60 minutes. It
                                                                             is not a demand forecast.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Recommendations                     HARDCODED                             One fixed overload playbook is selected by rule. It is not quantity-aware, SKU-
                                                                             aware, inventory-aware, or constraint-aware.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   LangGraph load_context              PLACEHOLDER                           Validates already-supplied evidence; it retrieves no context.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   LangGraph confidence nodes          PLACEHOLDER                           They append stage names; confidence was computed before graph entry.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   LangGraph widen_context             PLACEHOLDER                           Increments a retry counter without widening context or recalculating anything.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   LangGraph recommendation node       PLACEHOLDER                           Recommendation was selected before graph entry.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Explanation provider                REAL but limited                      Structured LLM output and deterministic fallback exist. Numeric grounding
                                                                             validation is useful, but semantic grounding is incomplete.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Fallback explanation                HARDCODED                             Fixed headline and probable-cause wording are emitted from signal presence.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Forecasting                         UNUSED / ABSENT                       There is no outlet × SKU × horizon demand forecast.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Trained model                       ABSENT                                No training pipeline, artifact, model registry, or model loading path exists.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Model evaluation                    ABSENT                                No time split, forecast metrics, baseline comparison, or model acceptance gate
                                                                             exists.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   External context                    ABSENT                                Weather, holiday, festival, events, traffic, and promotions do not enter
                                                                             intelligence.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Inventory intelligence              ABSENT                                Menu inventory appears in simulator constants but is not part of ingested order
                                                                             events or deterministic risk calculations.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Capacity intelligence               HARDCODED / INFERRED                  Capacity mismatch is inferred from anomaly combinations; no explicit throughput,
                                                                             staffing, or workload capacity model exists.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Driver attribution                  ABSENT                                Signal summaries exist, but there is no structured forecast attribution.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Historical decision memory          UNUSED / ABSENT                       Decisions and outcomes are stored, but no similarity retrieval influences later
                                                                             decisions.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   RAG                                 ABSENT                                No document ingestion, retrieval, embeddings, or vector store exists. This is
                                                                             currently appropriate.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Outcome verification                REAL but BROKEN semantically          It stores post-window metrics, but “three orders and zero cancellations” is enough
                                                                             to declare improvement. It does not compare prediction against actual, measure
                                                                             decision effect, or control for manager action.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Simulator                           SYNTHETIC BUT COMPUTED                Seeded and reproducible, and it uses POST /events; however its trajectory and
                                                                             recovery are scripted to produce the expected reactive incident.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Golden scenario                     HARDCODED                             The scenario predetermines degradation and recovery. It validates plumbing, not
                                                                             predictive correctness.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Main React incident pages           REAL                                  Fetch incidents, actions, outcomes, and summaries from backend APIs.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Additional dashboard/activity UI    HARDCODED                             Revenue, capacity, timing, outlet messages, shifts, and service-flow metrics come
                                                                             from apps/frontend/src/data/mock.ts.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Legacy “agents” package             UNUSED / MISLEADING                   These are deterministic wrappers, not autonomous agents; detector modules are the
                                                                             real implementation.
  ──────────────────────────────────  ────────────────────────────────────  ─────────────────────────────────────────────────────────────────────────────────────
   Standalone backend HTML demo        HARDCODED / PLACEHOLDER               Contains scripted chat behavior, seeded recovery behavior, fixed labels, and random
                                                                             visual timing.

  The current architecture documents also overstate some behavior. In particular, they describe comparable historical windows and local-time matching, while the
  backend currently uses contiguous UTC-aligned prior windows.

  No repository files were modified, and no test suite was run during this read-only architecture review.

  # B. What Is Fundamentally Wrong

  The current system predicts nothing about future restaurant demand. It detects degradation after orders, preparation delays, cancellations, and complaints have
  already occurred.

  The central conceptual problems are:

  1. The core grain is wrong. Intelligence operates at outlet × past event window, not outlet × SKU × future service window.
  2. It models observed operational symptoms, not latent customer demand.
  3. It lacks the state needed to reason about inventory: SKU quantities, recipes/yield, reservations, waste, replenishment, and safety buffers.
  4. It lacks explicit capacity supply: stations, staffing, preparation workload, throughput, and channel constraints.
  5. It has no forecast-safe feature policy and therefore no formal leakage protection.
  6. It has no reproducible training table, trained model, evaluation pipeline, or acceptance threshold.
  7. “Confidence” conflates evidence strength with predictive uncertainty.
  8. The recommendation is a fixed incident playbook, not a computed response to a projected shortage or overload.
  9. LangGraph mostly narrates an already-completed deterministic process.
  10. Outcome verification rewards scripted recovery without evaluating forecast accuracy or distinguishing association from causal impact.
  11. Persisted history is not retrieved for future decisions.
  12. Much of the frontend presents invented operational intelligence disconnected from backend facts.

  The existing reactive detectors remain useful as real-time monitoring and forecast residual checks. They should become a secondary feedback layer, not the
  primary intelligence product.

  # C. Proposed Target Architecture

  Use a modular monolith initially, retaining the current backend, intelligence package, PostgreSQL, Redis, simulator, and frontend boundaries.

  Internal events + external context + operational state
                            ↓
                Canonical signal ingestion
                            ↓
            Signal registry and quality validation
                            ↓
         Point-in-time feature snapshot construction
                            ↓
         Baseline forecast + accepted ML forecast
                            ↓
   Inventory projection             Capacity projection
            ↓                              ↓
   shortage/surplus risks            overload/oversell risks
                    ↓               ↓
               Structured driver evidence
                            ↓
                Deterministic decision engine
                            ↓
         Structured historical precedent retrieval
                            ↓
                   LangGraph orchestration
                            ↓
           Grounded LLM explanation or template
                            ↓
                 Manager review and action
                            ↓
                   Actual outcome ingestion
                            ↓
          Forecast and decision-cycle verification

  Ownership boundaries:

  - packages/intelligence/: contracts, registry, datasets, features, forecasts, projections, risks, attribution, decisions, and evaluation. Pure deterministic
    logic where practical.

  - apps/backend/src/intelligence/: orchestration, repositories, artifact loading, feature retrieval, persistence, and LangGraph integration.
  - PostgreSQL: signals, feature snapshots, forecasts, projections, decisions, actions, actuals, evaluation results, and structured history.
  - Redis: transport and work notification only.
  - Simulator: causal synthetic world generator calling normal ingestion APIs.
  - Frontend: rendering and user interaction only.
  - LLM: manager-readable language only.

  The current incident pipeline should coexist during migration. Predictive risk becomes the main product; reactive detectors validate emerging conditions and
  identify forecast misses.

  # D. Data / Signal Model

  Use a generic envelope with a typed value and extensible registry, not an ever-growing enum of rigid payload schemas.

  Proposed conceptual contract:

  Signal
    schema_version
    signal_id
    outlet_id
    entity_type
    entity_id
    observed_at
    effective_from
    effective_until
    source
    category
    signal_type
    value
    unit
    dimensions
    metadata
    quality
    provenance

  Important semantics:

  - observed_at: when LOSSLine learned the value.
  - effective_from / effective_until: period the value describes.
  - entity_id: SKU, order, station, staff pool, promotion, weather region, or outlet.
  - value: discriminated scalar types such as decimal, integer, boolean, categorical, timestamp, or bounded JSON structure.
  - dimensions: channel, service window, station, supplier, weather region, and similar query dimensions.
  - quality: completeness, validity, freshness, imputation status, and confidence supplied by the source.
  - provenance: provider, source record ID, ingestion time, transformation version, and synthetic lineage.

  The distinction between knowledge time and effective time is mandatory. A weather forecast issued at 08:00 for 18:00 is forecast-safe for a 10:00 prediction;
  an observation recorded at 19:00 is not.

  Raw source events and normalized signals should be separate concepts:

  - Raw events preserve source payloads for audit.
  - Normalized signals provide stable feature semantics.
  - Feature snapshots record exactly which signal versions were available at prediction time.

  The registry, not the schema, determines whether weather.rainfall_forecast_mm, inventory.usable_quantity, or a newly added factor is valid.

  # E. Prediction Targets

  Primary target:

  - latent_demand_quantity per outlet × SKU × service window.

  Because stockouts censor observed sales, training cannot always equate sales with demand. The first MVP can train on uncensored windows and explicitly flag
  censored windows; it must not silently treat capped sales as true demand.

  Required forecast outputs:

  - Point demand forecast.
  - Lower and upper prediction bounds.
  - Forecast horizon and as-of time.
  - Model/baseline version.
  - Data sufficiency and quality flags.
  - Supporting drivers.
  - Explicit abstention when inputs are inadequate.

  Separate downstream targets:

  - Observed sales quantity.
  - Stockout occurrence and time.
  - Fulfilled quantity.
  - Unfulfilled/cancelled quantity.
  - Preparation workload.
  - Capacity utilization and overload state.
  - Surplus quantity at window end.

  Stockout probability should not be emitted until calibrated probabilistic evaluation demonstrates reliability. Interval overlap and deterministic scenario-
  based risk can be used earlier without labeling it a probability.

  # F. Feature Strategy

  Every feature registry entry should define:

  - Name and semantic version.
  - Data type and unit.
  - Entity/grain.
  - Source.
  - Availability time.
  - Historical availability.
  - Future availability.
  - Transformation.
  - Missing-value strategy.
  - Forecast-safe flag.
  - Maximum acceptable staleness.
  - Leakage rationale.

  Initial feature families:

  - Demand history: lag 1, lag 2, lag 7 days, comparable-window median, rolling median, rolling mean, and recent trajectory.
  - Calendar: hour, service window, weekday, weekend, month, holiday, and festival.
  - External context: forecast temperature, forecast rainfall, forecast weather condition, and known local-event indicators.
  - Commercial: scheduled price, promotion type, discount, promotion age, and channel.
  - Operational supply context: opening usable inventory, planned replenishment, preparation capacity, staffing availability, and historical throughput.
  - Static dimensions: outlet and SKU attributes.

  Leakage controls:

  - Feature construction must accept an explicit prediction_as_of.
  - Every joined record must satisfy observed_at <= prediction_as_of.
  - Future-known values must have been published before the as-of time.
  - Actual weather, end-of-window inventory, realized cancellations, fulfilled quantity, and final preparation time cannot enter pre-window forecasts.
  - Dataset tests should deliberately inject future records and prove their exclusion.
  - Feature snapshots must persist provenance for replay.

  Inventory should generally not be a demand feature because it can encode censored sales and operational policy. It belongs primarily in the risk projection
  unless a carefully justified model needs availability-state features.

  # G. Forecasting Strategy

  Phase 1 baseline:

  - Comparable historical median at outlet × SKU × weekday/service-window grain.
  - Back off deterministically to SKU × service window, outlet × category, or global comparable windows when history is sparse.
  - Produce empirical residual intervals from historical forecast errors.
  - Persist forecasts and evaluation results.

  Phase 2 ML:

  - Practical gradient-boosted tabular regression.
  - Candidate library should be frozen after dependency and evaluation review; LightGBM, XGBoost, or another production-suitable boosted-tree implementation are
    reasonable.

  - Use time-ordered rolling-origin evaluation.
  - Train point forecasts first.
  - Add quantile models for lower/upper bounds only if coverage is evaluated.
  - Retain the baseline as a fallback and benchmark.

  Evaluation:

  - MAE and RMSE.
  - WMAPE where total demand is nonzero.
  - Bias by outlet, SKU, window, and demand band.
  - Prediction-interval coverage and width if intervals are offered.
  - Stockout/overstock decision performance downstream.
  - Performance on each golden scenario.
  - Model accepted only if it materially improves the agreed primary metric without unacceptable subgroup regressions.

  Model artifacts must include training cutoff, dataset fingerprint, feature registry version, code version, parameters, metrics, and serialized artifact
  checksum.

  # H. Inventory / Capacity Risk Strategy

  Inventory projection must be deterministic:

  usable_supply
    = on_hand
    - unusable_or_reserved
    + confirmed_replenishment_before_need

  projected_ending_inventory
    = usable_supply
    - expected_demand
    - safety_buffer

  predicted_shortage
    = max(0, expected_demand + safety_buffer - usable_supply)

  predicted_surplus
    = max(0, usable_supply - expected_demand - target_closing_stock)

  Stockout time should be derived from the cumulative intrawindow demand curve, not by evenly dividing total demand unless that approximation is explicitly
  versioned and documented.

  Capacity must be modeled separately:

  predicted_workload_minutes
    = Σ(predicted_sku_quantity × standard_workload_per_sku)

  available_capacity_minutes
    = effective_staff_or_station_capacity
      × service_window_minutes
      × availability_factor

  Capacity risk then compares workload with available throughput and queue state. Initial risk tiers can be deterministic:

  - NORMAL
  - ELEVATED
  - HIGH_OVERLOAD_RISK

  Inventory shortage, capacity overload, and delivery oversell must remain distinct risk types even when they occur together.

  Forecast uncertainty should be propagated using lower/point/upper demand scenarios. This provides defensible risk bands without fabricating probabilities.

  # I. Decision Engine Design

  Input:

  - Forecast and uncertainty.
  - Inventory projection.
  - Capacity projection.
  - Structured risk candidates.
  - Deterministic drivers.
  - Operational constraints.
  - Relevant historical precedents.
  - Policy limits.

  Output contract:

  DecisionCandidate
    decision_id
    outlet_id
    sku_id
    service_window
    risk_type
    recommended_action
    recommended_quantity
    execute_by
    reason_code
    supporting_evidence
    urgency
    forecast_confidence
    action_risk
    requires_approval
    constraints_considered
    rule_version
    created_at

  Rules should be quantity-aware. For example, replenishment or prep quantity should derive from projected shortage, package/yield size, waste risk, maximum safe
  batch, lead time, and upper forecast bound.

  Confidence and action risk are separate:

  - Forecast confidence concerns prediction reliability and data quality.
  - Action risk concerns waste, cost, reversibility, customer impact, and policy limits.

  NO_ACTION must be a first-class, persisted decision. Abstention must also be explicit when data or policy is insufficient.

  # J. RAG Boundary

  RAG is not part of numerical prediction.

  Allowed retrieval sources:

  - SOPs.
  - Supplier lead-time documents.
  - Inventory and food-safety policies.
  - Manager notes.
  - Unstructured incident and outcome summaries.

  Structured PostgreSQL retrieval should come first for:

  - Same outlet and SKU.
  - Same service window.
  - Same risk and action.
  - Similar forecast-to-inventory ratio.
  - Similar weather, promotion, or event context.
  - Prior manager decision and observed outcome.

  A vector database is not justified until a meaningful unstructured corpus exists and retrieval evaluation demonstrates that lexical/metadata retrieval is
  insufficient.

  Retrieved content may constrain or contextualize a decision. It may not overwrite forecasts, quantities, confidence, or deterministic risk results.

  # K. LangGraph Design

  Use a ForecastInvestigationState containing immutable references to persisted artifacts:

  - Prediction as-of and horizon.
  - Outlet, SKU, and service window.
  - Feature snapshot ID.
  - Forecast ID.
  - Inventory and capacity projection IDs.
  - Risk candidates.
  - Driver evidence.
  - Historical context.
  - Decision candidate.
  - Explanation.
  - Validation result.
  - Approval and outcome state.

  Meaningful graph:

  START
    → collect_context
    → build_features
    → forecast_demand
    → project_inventory
    → project_capacity
    → assess_risks
    → attribute_drivers
    → retrieve_relevant_history
    → generate_decision
    → explain
    → validate
    → manager_review
    → END

  Each node must either compute a real artifact, retrieve persisted evidence, validate an invariant, or manage a genuine workflow transition. Nodes that only
  append stage names should be removed.

  The graph should orchestrate package functions; it should not contain forecasting or business formulas. Manager review should use durable checkpoint/resume
  semantics when introduced.

  # L. Verification Architecture

  Verification has three layers.

  Engineering verification:

  - Contract tests for every persisted and API model.
  - Unit tests for feature availability, leakage guards, forecasting, projections, risks, attribution, and decisions.
  - Integration tests across ingestion, PostgreSQL, model artifacts, orchestration, APIs, and frontend contracts.
  - Reproducibility checks using dataset and artifact hashes.

  Forecast verification:

  - Persist prediction and actual at identical grain.
  - Calculate errors after the target window closes.
  - Monitor bias and accuracy by outlet, SKU, horizon, window, and scenario.
  - Track interval coverage if intervals are published.
  - Record missing/censored outcomes explicitly.

  Decision verification:

  - Persist recommendation, manager choice, executed action, and outcome.
  - Compare projected versus actual shortage, stockout time, workload, and surplus.
  - Evaluate operational usefulness and action adherence.
  - Never claim the recommendation caused an outcome without a valid causal design.

  Chunk gate:

  Specification
    → decision record
    → implementation
    → unit tests
    → integration tests
    → golden scenario
    → verification report
    → pass/fail gate

  A chunk cannot close with failing required tests, missing evidence, unreconciled leakage, or undocumented architectural changes.

  # M. Proposed Implementation Chunks

  - C0 — Architecture, contracts, terminology, decision records, and migration/coexistence boundaries.
  - C1 — Generic signal contract, registry, provenance, quality, and forecast-safety enforcement.
  - C2 — Seeded causal synthetic world generator and six deterministic golden scenarios.
  - C3 — Point-in-time outlet × SKU × window dataset and feature engineering.
  - C4 — Comparable-history baseline forecast and baseline evaluation.
  - C5 — Boosted-tree forecast, artifact management, and prediction intervals.
  - C6 — Time-based evaluation, subgroup analysis, model acceptance gate, and reproducibility.
  - C7 — Inventory state and deterministic inventory projection.
  - C8 — Workload, throughput, capacity, and oversell-risk projection.
  - C9 — Deterministic and model-derived driver attribution.
  - C10 — Quantity-aware decision engine and abstention policy.
  - C11 — Prediction/decision-cycle persistence and structured historical retrieval.
  - C12 — Optional document retrieval using PostgreSQL metadata/text search first.
  - C13 — Meaningful LangGraph orchestration and durable review transitions.
  - C14 — Grounded structured explanation, validation, and deterministic fallback.
  - C15 — Backend APIs, schedulers, artifact loading, and reactive/predictive coexistence.
  - C16 — Forecast-first frontend and removal of disconnected mock intelligence.
  - C17 — Actual-outcome ingestion, forecast verification, and decision evaluation.
  - C18 — Complete seeded golden demo with reproducible verification evidence.

  For each chunk, the specification should be frozen before implementation and should produce its required CHUNK_<ID>.md and verification/C<ID>_VERIFICATION.md.

  # N. Decisions That Must Be Frozen Before Coding

  1. Forecast grain: hourly versus named service windows.
  2. Forecast horizon and daily prediction schedule.
  3. Definition of demand versus observed/censored sales.
  4. SKU identity, substitutions, bundles, modifiers, and recipe/yield treatment.
  5. Inventory units and conversion rules.
  6. Baseline comparison hierarchy and minimum history.
  7. Primary model-acceptance metric and required improvement.
  8. Prediction interval method and target coverage.
  9. Feature knowledge-time and late-arriving-data policy.
  10. Weather forecast-vintage policy.
  11. Holiday, festival, promotion, and local-event source semantics.
  12. Synthetic causal assumptions and scenario parameters.
  13. Inventory safety-buffer and surplus policy.
  14. Capacity units and workload estimation method.
  15. Decision quantity rounding, maximum batch, lead-time, and approval limits.
  16. Forecast confidence representation.
  17. Driver attribution method and wording limitations.
  18. Structured-history similarity criteria.
  19. Conditions that would justify RAG or a vector database.
  20. LangGraph checkpoint and manager-review lifecycle.
  21. Coexistence and eventual disposition of the reactive incident pipeline.
  22. Model artifact storage and deployment strategy.
  23. Outcome maturity windows and censored/missing-outcome rules.
  24. Data retention and replay policy.
  25. MVP outlet, SKU catalog, timezone, and service-window configuration.

  # O. Risks / Landmines

  - Treating sales during stockouts as true demand will systematically underforecast.
  - Using actual weather instead of forecast vintages will leak future information.
  - Random train/test splits will produce misleadingly strong results.
  - Synthetic data that encodes the model’s exact rules will create circular evaluation.
  - One synthetic seed or one outlet can make model comparisons meaningless.
  - High-cardinality outlet/SKU encoding can overfit sparse entities.
  - Promotions and local events may be confounded with outlet or weekday patterns; attribution must not be presented as causality.
  - Prediction intervals can be badly calibrated even when point MAE improves.
  - WMAPE can hide severe low-volume SKU errors.
  - Forecast accuracy can improve while operational decisions worsen due to asymmetric shortage and waste costs.
  - Inventory snapshots may be stale, incorrectly unitized, or inconsistent with recipe yield.
  - Capacity is nonlinear: stations, batching, SKU mix, and queue state matter more than a single orders-per-hour number.
  - Scripted post-approval recovery cannot validate decision effectiveness.
  - Existing fixture baseline filling masks sparse evidence and must not enter predictive training.
  - The current simulator does not carry SKU identity through canonical order data despite selecting SKUs internally.
  - Existing database columns use floats for some derived metrics, conflicting with the stated Decimal discipline.
  - Current outcome verification can label an incident improved without comparing against the original degraded metrics.
  - LLM numeric grounding checks do not prevent unsupported qualitative claims.
  - Frontend mock metrics can make the product appear predictive before backend capability exists.
  - Reusing the current Signal anomaly model for generic observations without a terminology migration could create two incompatible meanings of “signal.”
  - Replacing the current pipeline in one step would risk losing a functioning ingestion and reactive monitoring path; migration should be incremental and
    contract-driven.