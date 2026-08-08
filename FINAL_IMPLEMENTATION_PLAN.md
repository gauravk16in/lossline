# LOSSLine — FINAL_IMPLEMENTATION_PLAN.md

One-line goal: three developers deliver a reproducible synthetic restaurant demo in which live operational events produce an evidence-grounded lunch-rush incident, an advisory action requiring manager approval, and a measured post-action outcome. (user: accepted Q2 recommendation; verified: `docs/Restaurant Implementation Plan.md` §§1–4)

## Document Status and Evidence Convention

This document supersedes `IMPLEMENTATION_PLAN.md` for implementation and is the sole input to the later architecture document. (user: requested finalization before architecture)

Statements carry one status: `(user)` records an interview decision; `(verified: source)` records an artifact finding; `[assumed: default — if wrong: consequence]` records a reversible default that must be verified in Phase 1. Prescriptive requirements use `FROZEN`, while numeric operating values use `CONFIG_DEFAULT` unless the supplied documents establish them. (verified: `/Users/kr/Desktop/Lossline/The Refined Meta-Prompt.md`, Evidence discipline)

## Classification and Interview Ledger

Track: from-scratch product implementation plan; the repository contains planning documents and empty component directories but no application manifests or source code. (verified: `find . -type f` and `find . -maxdepth 3 -type d`, run during this review)

- Q1, PRD access → `product-req.pdf` supplied. (user)
- Q2, demo scenario → lunch-rush operational overload accepted. (user)
- Q3, processing → Redis Streams accepted for the MVP event path. (user)
- Q4, realtime UI → WebSocket accepted, with REST authoritative. (user)
- Q5, orchestration → LangGraph accepted only after deterministic detection. (user)

Questions used: 5 of 5. (verified: interview ledger above)

## Red-Team Findings and Resolutions

| Candidate-plan issue | Evidence | Final resolution |
|---|---|---|
| The candidate chose lunch rush while the PRD separately demonstrates weather-driven delivery and payment-gateway failures. | (verified: `IMPLEMENTATION_PLAN.md` §1; `product-req.pdf` pp. 9, 13–14) | Freeze lunch rush; park both PRD examples. (user) |
| The candidate replaced Redis Streams with an in-process job. | (verified: `IMPLEMENTATION_PLAN.md` §8; `product-req.pdf` pp. 3–5) | Redis `restaurant.events` is the mandatory normalized-event handoff. (user) |
| The candidate used polling and omitted the live pipeline. | (verified: `IMPLEMENTATION_PLAN.md` §20; `product-req.pdf` pp. 9–11) | WebSocket carries transient live transitions; REST remains authoritative. (user) |
| The candidate made LangGraph optional. | (verified: `IMPLEMENTATION_PLAN.md` §21; `product-req.pdf` pp. 3, 6–8) | LangGraph is mandatory after an incident candidate, never per event. (user) |
| The candidate silently selected 30-minute windows, seven-day history, thresholds, and score weights. | (verified: `IMPLEMENTATION_PLAN.md` §§9–13) | Treat every such number as versioned configuration default with fixture-based calibration. [assumed: defaults below — if wrong: configuration and golden fixtures change, not contracts] |
| Revenue at risk, live analytics, approval expiry, incident deduplication, and durable consumer recovery were missing or incomplete. | (verified: comparison of `IMPLEMENTATION_PLAN.md` with `product-req.pdf` pp. 9–13) | Specify revenue estimate and deduplication; include only demo-serving live pipeline and summary; defer broad analytics and external notification channels. [assumed: narrow MVP — if wrong: frontend/API scope expands] |
| The PRD claims historical memory influences investigations, but the candidate had no M1 retrieval behavior. | (verified: `product-req.pdf` pp. 7, 11, 14; `IMPLEMENTATION_PLAN.md`) | Persist outcomes in M1; defer memory-influenced recommendations and Copilot until multiple meaningful incidents exist. [assumed: honest demo claim preferred — if wrong: add seeded historical incidents and retrieval acceptance tests] |
| The PRD’s “specialist agents” wording could overstate deterministic calculations as AI. | (verified: `product-req.pdf` pp. 6, 12; `docs/Restaurant Implementation Plan.md` §5) | Call them deterministic specialist nodes in code and UI; reserve LLM use for grounded prose. [assumed: accurate presentation wording — if wrong: presentation copy changes, not logic] |

## Frozen MVP Scope

FROZEN: the M1 scenario uses four source domains: POS orders, KDS preparation, delivery handoff/cancellation, and customer reviews. (user: accepted lunch-rush recommendation; verified: `docs/Restaurant Implementation Plan.md` §§3, 8)

FROZEN: the observable flow is scenario runner → `POST /events` → validation/normalization/deduplication → PostgreSQL raw event → Redis `restaurant.events` → deterministic aggregation/detection → incident candidate → LangGraph investigation → deterministic confidence/recommendation/revenue estimate → manager approval → simulated action/recovery → outcome verification. (user: Q3–Q5; verified: `product-req.pdf` pp. 3–10)

FROZEN: all restaurant data and UI metrics display “Synthetic data for demonstration.” (verified: `docs/Restaurant Implementation Plan.md` §2)

FROZEN: M1 ships outlet health, live pipeline, incident investigation, approval, and outcome views; it does not ship a generic BI product. (verified: `docs/Restaurant Implementation Plan.md` §13; `product-req.pdf` pp. 10–11)

## Explicit Non-Goals

- Real POS, KDS, delivery, review, payment, inventory, weather, or staffing integrations are not MVP work. (verified: `product-req.pdf` p. 3)
- Weather-driven delivery and payment-gateway demo scenarios are deferred because only one scenario is frozen. (user: Q2)
- Inventory, payment, weather, staffing, stockout, refund, and sales-drop detectors are deferred. (verified: frozen source list above)
- Automatic real-world action execution is prohibited; approval changes simulator behavior only. (verified: `product-req.pdf` p. 8)
- SMS, email, Slack, Teams, push notifications, AI Copilot, vector search, learned confidence calibration, full analytics, multi-tenant hardening, Kubernetes, and microservice extraction are deferred. [assumed: narrow hackathon MVP — if wrong: architecture and delivery schedule expand materially]
- Outcome improvement is not proof that the action caused the change; UI and explanations must not claim causality. (verified: `docs/Restaurant Implementation Plan.md` §§3, 5)

## Assumptions Ledger

| ID | Assumption/default | Basis | Blast radius if wrong | Required check |
|---|---|---|---|---|
| A1 | One-machine Docker Compose demo deployment. | PRD names Docker; no host is specified. (verified: `product-req.pdf` pp. 10–11) | Deployment topology and secrets handling change. | Phase 1 confirms target machine can run the chosen container tooling. |
| A2 | Python/FastAPI backend, PostgreSQL, Redis Streams, React/TypeScript, LangGraph, and a provider-backed LLM interface; exact versions are unresolved. | Stack named in PRD. (verified: `product-req.pdf` pp. 10–11) | Scaffolding and APIs may change. | Phase 1 selects mutually compatible current versions and commits lockfiles. |
| A3 | A 30-minute event-time window sliding every five minutes. | Existing candidate default; no PRD value. (verified: `IMPLEMENTATION_PLAN.md` §9) | Metrics, latency, thresholds, and simulator pacing change. | Phase 2 runs the golden scenario and adjusts config before detector breadth. |
| A4 | Baseline is the median of comparable restaurant/local-time windows across seven synthetic days; MAD estimates dispersion. | Existing candidate default; no PRD algorithm. (verified: `IMPLEMENTATION_PLAN.md` §9) | Simulator prelude and anomaly magnitudes change. | Phase 2 validates baseline stability and sparse-data behavior. |
| A5 | Thresholds, weights, minimum samples, confidence cutoffs, and outcome deltas below are configuration defaults, not business truths. | User explicitly prohibited treating numbers as facts. (user) | Incident behavior and demo timing change. | Phase 2 calibration report records fixture results and frozen demo config. |
| A6 | One Redis consumer group processes normalized events; PostgreSQL remains the source of truth. | Simplest implementation satisfying Redis decision. [assumed: one consumer group — if wrong: consumer topology and ownership change] | Recovery and scale design change. | Phase 1 proves claim-after-crash and idempotent replay. |
| A7 | One WebSocket endpoint broadcasts non-durable transition notifications; REST reloads state after connect/reconnect. | Accepted recommendation. (user) | Realtime protocol and frontend store change. | M0 disconnect/reconnect integration test. |
| A8 | One manager identity string is accepted from demo UI; production authentication is absent. | PRD excludes production-grade tenant security. (verified: `product-req.pdf` p. 3) | Approval audit/auth design changes. | Phase 1 confirms demo exposure is private/local; otherwise add auth before deployment. |
| A9 | Revenue currency is restaurant-configured and the demo uses INR; forecast horizon defaults to 60 minutes. | PRD shows ₹ but specifies no general currency/horizon. (verified: `product-req.pdf` pp. 13–14) | Impact display and formula inputs change. | Phase 2 confirms demo values and labels estimate assumptions. |
| A10 | LangSmith tracing is disabled unless credentials already exist as `${LANGSMITH_API_KEY}`. | PRD recommends LangSmith but no credentials are present. (verified: `product-req.pdf` pp. 10–11; repository file scan) | Remote tracing availability changes. | Phase 1 detects configuration; structured local logs are fallback. |

No assumption may silently become an architectural requirement; Phase 1 records accepted values in versioned configuration and an ADR-style decision log. (verified: `/Users/kr/Desktop/Lossline/The Refined Meta-Prompt.md`, completeness and executor gates)

## Technology Decisions

- FROZEN: FastAPI receives REST events and serves state APIs because the supplied requirements name it. (verified: `product-req.pdf` pp. 3, 10)
- FROZEN: PostgreSQL stores durable domain state and JSON event payloads. (verified: `product-req.pdf` pp. 7, 10)
- FROZEN: Redis Streams transports normalized operational events asynchronously; only `restaurant.events` exists in M1. (user: Q3)
- FROZEN: LangGraph coordinates post-detection investigation, the bounded retry, approval interrupt/resume, and persistence. (user: Q5)
- FROZEN: REST is authoritative and WebSocket is transient presentation delivery. (user: Q4)
- CONFIG_DEFAULT: React with TypeScript implements the web UI; the exact build tool and library versions are selected in Phase 1. [assumed: PRD-named frontend — if wrong: frontend scaffold changes]
- CONFIG_DEFAULT: an in-process scheduler triggers outcome checks; a separate worker is unnecessary at demo scale. [assumed: single-host demo — if wrong: schedule ownership and deployment topology change]
- FROZEN: LLM output never calculates metrics, confidence, revenue impact, recommendation selection, or outcome status. (verified: `docs/Restaurant Implementation Plan.md` §5)

## Repository Structure

```text
apps/
  backend/
    app/{api,config,db,ingestion,streaming,realtime,incidents}/
    migrations/
    tests/{unit,integration,contract}/
  frontend/
    src/{api,components,pages,realtime,state,types}/
    tests/
services/
  intelligence/
    lossline_intelligence/{aggregation,detectors,correlation,confidence,impact,recommendations,workflow}/
    tests/
simulator/
  lossline_simulator/{fixtures,scenarios,runner}/
  tests/
docs/{decisions,demo}/
docker-compose.yml
```

WHAT: one deployable backend imports a pure intelligence package; simulator and frontend remain separate processes. WHY: it permits three-person parallel work without inventing service boundaries. INPUT: frozen contracts. OUTPUT: importable packages and runnable applications. OWNER: Person 2 scaffolds backend/simulator, Person 1 intelligence, Person 3 frontend. DEPENDENCIES: A1–A2 checks. FAILURE BEHAVIOR: setup exits with a named missing dependency/configuration error. DEFINITION OF DONE: a clean checkout runs the documented format, lint, type-check, unit-test, and container startup commands. [assumed: modular-monolith layout — if wrong: package paths change before M0]

## Canonical Event Contracts

The API accepts one canonical envelope; the simulator must not bypass it. (verified: `product-req.pdf` pp. 4–5, 9)

```json
{
  "schema_version": "1.0",
  "event_id": "evt_001",
  "restaurant_id": "store_17",
  "source": "pos",
  "event_type": "order.created",
  "occurred_at": "2026-08-08T07:40:00Z",
  "entity": {"type": "order", "id": "ord_001"},
  "data": {},
  "metadata": {"synthetic": true, "scenario_id": "lunch_rush_v1", "sequence": 1}
}
```

FROZEN envelope rules: identifiers are non-empty strings; timestamps include offsets and normalize to UTC; `schema_version`, `source`, and `event_type` are enumerated; `data` uses a discriminated Pydantic model; server-set `received_at` is not accepted from clients; payload size is bounded by configuration. [assumed: validation rules — if wrong: compatibility surface changes before M0]

M1 event types and required `data` fields are:

| Event | Required data | Metric use |
|---|---|---|
| `order.created` | `channel`, `amount`, `currency` | order velocity and average order value |
| `order.completed` | `channel`, `amount`, `currency` | completed revenue |
| `preparation.completed` | `order_id`, `duration_seconds` | mean/p90 preparation time |
| `delivery.handoff_completed` | `order_id`, `wait_seconds` | handoff delay |
| `order.cancelled` | `channel`, `amount`, `currency`, `reason_code` | cancellation rate and lost booked value |
| `review.received` | `rating`, `text`, `language` | negative rating and delay-keyword evidence |

The event list is a CONFIG_DEFAULT mapping of the frozen four sources; changing fields requires schema-version and contract-fixture changes. [assumed: event detail — if wrong: API, simulator, metrics, and tests change together]

WHAT: validate heterogeneous synthetic observations into one stable contract. WHY: every downstream stage must interpret the same identifiers, time, money, and source semantics. INPUT: HTTP JSON. OUTPUT: canonical event plus server `received_at`. OWNER: Persons 1 and 2 jointly freeze fixtures; Person 2 implements. DEPENDENCIES: restaurant configuration and A2. FAILURE BEHAVIOR: malformed events return `422` problem details and are neither persisted nor published. DEFINITION OF DONE: one valid and one invalid fixture per event type pass contract tests; TypeScript types are generated or checked against the same OpenAPI schema. [assumed: OpenAPI contract workflow — if wrong: manual type fixtures must provide equivalent checks]

## Database Model

- `restaurants(id, name, timezone, currency, synthetic, metadata, created_at)`
- `events(id, event_id UNIQUE, restaurant_id FK, source, event_type, occurred_at, received_at, entity JSONB, data JSONB, metadata JSONB, schema_version, payload_hash)`
- `metric_windows(id, restaurant_id FK, window_start, window_end, metric_name, value, sample_count, baseline_value, dispersion, config_version, UNIQUE(...))`
- `signals(id, restaurant_id FK, signal_type, severity, current_value, baseline_value, deviation, unit, window_start, window_end, evidence_event_ids JSONB, detector_version, UNIQUE(...))`
- `incidents(id, restaurant_id FK, incident_type, status, severity, confidence, confidence_components JSONB, probable_cause, explanation, revenue_at_risk, currency, window_start, window_end, correlation_rule_version, config_version, created_at, updated_at)`
- `incident_signals(incident_id FK, signal_id FK, PRIMARY KEY(...))`
- `recommendations(id, incident_id FK, rule_id, action_text, expected_impact JSONB, urgency, risk_tier, source, expires_at, created_at)`
- `actions(id, recommendation_id FK, decision, suggested_text, final_text, decided_by, decided_at, execution_status, executed_at, manager_note, idempotency_key UNIQUE)`
- `outcomes(id, incident_id FK, status, baseline_metrics JSONB, post_metrics JSONB, check_after, evaluated_at, rule_version, UNIQUE(incident_id))`
- `scenario_runs(id, scenario_id, seed, speed, status, started_at, completed_at)`

WHAT: preserve source evidence, derived values, decisions, and outcomes with audit timestamps. WHY: REST, reconnects, retries, explanations, and verification cannot depend on Redis or WebSocket history. INPUT: canonical events and deterministic stage outputs. OUTPUT: queryable authoritative state. OWNER: Person 2. DEPENDENCIES: contracts and lifecycle. FAILURE BEHAVIOR: transaction rolls back the current stage; Redis message remains pending for retry. DEFINITION OF DONE: migrations upgrade/downgrade a disposable database, uniqueness/index constraints have integration tests, and an incident traces to its source events. [assumed: normalized table set — if wrong: migrations and repositories change before M0]

## API and Frontend Contract

- `POST /api/v1/events` → `202 {event_id, status:"accepted", duplicate}` after durable event insert and Redis publication; identical duplicate returns the original acceptance, conflicting duplicate returns `409`. [assumed: response semantics — if wrong: simulator contract changes]
- `POST /api/v1/demo/runs` → starts `{scenario_id, seed, speed}`; `POST /api/v1/demo/reset` → deletes synthetic run-derived records only after validating demo mode. (verified: `product-req.pdf` p. 10; [assumed: safer resource shape — if wrong: route names change])
- `GET /api/v1/restaurants` → restaurant health cards, current metrics, active incident count, synthetic flag. [assumed: consolidated outlet contract — if wrong: UI request model changes]
- `GET /api/v1/incidents` → cursor-paginated feed filtered by restaurant/status/confidence tier. (verified: `product-req.pdf` pp. 10, 12)
- `GET /api/v1/incidents/{id}` → evidence, score components, revenue estimate inputs, recommendation, action, and outcome. (verified: `product-req.pdf` pp. 10–11)
- `POST /api/v1/incidents/{id}/decision` → `{decision: APPROVE|REJECT|EDIT, final_action_text?, manager_note?, idempotency_key}`. [assumed: one transition endpoint — if wrong: split approve/reject endpoints without changing domain service]
- `GET /api/v1/incidents/{id}/outcome` → outcome or `INSUFFICIENT_DATA` plus `check_after`. (verified: `docs/Restaurant Implementation Plan.md` §10)
- `GET /api/v1/analytics/summary` → only demo headline totals needed by outlet health; broad charts are deferred. [assumed: narrow PRD endpoint — if wrong: analytics aggregation scope expands]
- `WebSocket /ws?run_id=...` → transition messages `{message_id, run_id, incident_id?, stage, status, occurred_at}`; messages contain IDs and display-safe summaries, not authoritative domain objects. (user: Q4; [assumed: message envelope — if wrong: frontend realtime adapter changes])

WHAT: expose state and manager commands while separately broadcasting live progress. WHY: REST supports reliable reload; WebSocket makes the judged pipeline visible. INPUT: validated commands and filters. OUTPUT: versioned JSON/problem details plus transient notifications. OWNER: Person 2 owns REST/WebSocket server; Person 3 owns generated client and reconnection. DEPENDENCIES: database, lifecycle, A7. FAILURE BEHAVIOR: WebSocket loss shows “reconnecting” and triggers REST refresh; command failures show actionable problem text and preserve current state. DEFINITION OF DONE: OpenAPI snapshot tests, approve/reject/edit contract tests, and a disconnect/reconnect browser test pass. (user: Q4; [assumed: versioned `/api/v1` — if wrong: route prefix changes before frontend integration])

## Ingestion and Redis Pipeline

1. FastAPI validates and normalizes the event. 2. A database transaction inserts `events` plus an outbox record. 3. An outbox publisher appends the event to `restaurant.events` and marks publication complete. 4. Consumer group `detection` reads it, updates affected event-time windows, persists derived results, broadcasts stage notifications, and acknowledges only after commit. [assumed: transactional outbox — if wrong: a crash between DB and Redis can lose or duplicate work]

The consumer is at-least-once; every derived write is idempotent by restaurant, window, type, and version. Pending messages are reclaimed after a configurable idle timeout. Event ordering uses `occurred_at` for windows and Redis order only for delivery; events older than the configurable lateness watermark are stored but do not silently rewrite resolved incidents. [assumed: recovery model — if wrong: duplicate and late-event behavior becomes undefined]

WHAT: hand accepted events safely to asynchronous detection. WHY: the PRD and accepted decision require a visible streaming boundary without making Redis durable truth. INPUT: canonical stored event/outbox. OUTPUT: acknowledged stream message and updated windows/signals. OWNER: Person 2. DEPENDENCIES: Redis, PostgreSQL, event schema. FAILURE BEHAVIOR: Redis outage leaves outbox rows pending and returns event acceptance only after durable storage; consumer crash leaves messages claimable; poison events move to a named dead-letter stream after configurable attempts. DEFINITION OF DONE: tests kill publisher and consumer between each state transition and prove eventual processing without duplicate incidents. [assumed: outbox and dead-letter implementation — if wrong: reliability claims must be removed from presentation]

## Aggregation and Historical Baseline

CONFIG_DEFAULT A3: compute event-time 30-minute windows every five minutes per restaurant. Metrics are orders/minute, delivery orders, cancellation count/rate, mean and p90 preparation seconds, mean handoff wait, negative review count/rate, delay-keyword count, average order value, and completed/cancelled value. (verified: scenario requirements in `docs/Restaurant Implementation Plan.md` §3; defaults in A3)

CONFIG_DEFAULT A4: compare against the median and MAD of matching restaurant/local weekday/time windows from seven synthetic baseline days. If fewer than four comparable windows exist, mark baseline quality insufficient; if MAD is zero, use a metric-specific absolute business threshold. [assumed: baseline sufficiency/default — if wrong: baseline logic and simulation history change]

WHAT: turn individual events into comparable operational measurements. WHY: detectors must use stable deterministic inputs rather than LLM judgment. INPUT: stored canonical events, restaurant timezone, window config. OUTPUT: versioned metric snapshot with sample counts and quality flags. OWNER: Person 1 logic, Person 2 query adapter. DEPENDENCIES: event contract and baseline fixtures. FAILURE BEHAVIOR: sparse/missing data produces quality flags and abstention, never division-by-zero or fabricated baselines. DEFINITION OF DONE: tests cover UTC/local boundaries, zero denominator, sparse baseline, late event, and deterministic replay; golden scenario shows normal then degraded snapshots. [assumed: window mechanics — if wrong: CONFIG_DEFAULT changes only]

## Detector Specifications

| Signal | CONFIG_DEFAULT trigger | Evidence |
|---|---|---|
| `ORDER_VOLUME_SPIKE` | current order rate ≥ baseline × 1.30, robust z-score ≥ 2, minimum 10 orders | created order IDs and window metric |
| `PREP_TIME_SPIKE` | mean preparation ≥ baseline × 1.40 and minimum 8 completed preparations | preparation event IDs and mean/p90 |
| `HANDOFF_DELAY_SPIKE` | mean wait ≥ baseline × 1.40 and minimum 8 handoffs | handoff event IDs and mean |
| `CANCELLATION_SPIKE` | rate ≥ baseline + 0.05 and ≥ baseline × 2 with minimum 10 orders and 3 cancellations | created/cancelled IDs and rates |
| `DELAY_REVIEW_SPIKE` | at least 2 ratings ≤ 2 containing a configured delay term | review IDs, ratings, matched normalized terms |

Every numeric trigger is versioned configuration under A5 and must be calibrated against normal, true-positive, and near-threshold fixtures before M1. (user: numeric values are not facts)

WHAT: emit structured signals for abnormal operational metrics. WHY: routine events must not invoke LangGraph or an LLM. INPUT: metric snapshot and baseline. OUTPUT: zero or one signal per type/window/version with severity `[0,1]`. OWNER: Person 1. DEPENDENCIES: aggregation and config. FAILURE BEHAVIOR: missing/low-quality inputs return no signal plus a diagnostic reason; detector exceptions fail the window and retry rather than producing partial correlation. DEFINITION OF DONE: below/at/above threshold, sparse-data, and repeatability tests pass for every detector. (verified: deterministic detector requirement in `product-req.pdf` pp. 5–6)

## Incident Correlation and Deduplication

CONFIG_DEFAULT overload rule: `ORDER_VOLUME_SPIKE` and `PREP_TIME_SPIKE` are required antecedents; at least one of `HANDOFF_DELAY_SPIKE` or `CANCELLATION_SPIKE` is required impact evidence; `DELAY_REVIEW_SPIKE` strengthens corroboration. Signals must share a restaurant and overlap the candidate window or end within 60 configured minutes. [assumed: rule shape — if wrong: incident firing behavior changes]

Create an incident fingerprint from `(restaurant_id, incident_type, correlation_rule_version)`. If an `OPEN`, `AWAITING_APPROVAL`, `ACTION_APPROVED`, or `VERIFYING` incident with that fingerprint has a last evidence window within a configurable 60 minutes, update it with new unique signals and recompute derived fields; otherwise create a new incident. Resolved/rejected incidents are never reopened by late events. [assumed: dedup policy — if wrong: alert count, lifecycle, and demo UI change]

WHAT: convert temporally aligned evidence into one operational episode and suppress repeated alerts. WHY: independent threshold signals are not yet an explanation, and duplicate notifications would misrepresent incident count. INPUT: persisted signals. OUTPUT: new/updated incident candidate and linked evidence. OWNER: Person 1 rule, Person 2 transactional persistence. DEPENDENCIES: signals, lifecycle. FAILURE BEHAVIOR: ambiguous/missing required signals remain uncorrelated; concurrent updates rely on a transaction/advisory lock and retry. DEFINITION OF DONE: positive, missing-evidence, separated-time, cross-restaurant, concurrent, late-event, and resolved-incident tests pass. [assumed: locking mechanism is executor choice — if wrong: equivalent uniqueness control required]

## Deterministic Confidence

CONFIG_DEFAULT components are normalized to `[0,1]`:

```text
severity     = weighted mean of correlated signal severities
coverage     = present evidence weight / eligible evidence weight
alignment    = max(0, 1 - evidence_span_minutes / configured_span_limit)
data_quality = mean(sample_sufficiency, baseline_sufficiency, freshness)
confidence   = min(0.95,
                   0.35*severity + 0.30*coverage +
                   0.20*alignment + 0.15*data_quality)
```

CONFIG_DEFAULT evidence weights: volume `.20`, preparation `.30`, handoff `.15`, cancellations `.25`, reviews `.10`. Confidence `<.50` triggers exactly one LangGraph retry with an evidence range widened by one hour on each side; if still `<.50`, status is `MONITOR_ONLY`, no recommendation is created, and execution stops. `.50–.74` is review-required; `.75–.95` is high confidence but still requires approval in M1. [assumed: formula/weights/cutoffs from candidate and PRD — if wrong: config and calibration fixtures change]

WHAT: quantify evidence strength reproducibly and expose its components. WHY: confidence cannot be delegated to an LLM. INPUT: correlated signals, baseline/sample quality, evidence times. OUTPUT: score, tier, component values, config version. OWNER: Person 1. DEPENDENCIES: correlation. FAILURE BEHAVIOR: non-finite/missing components force low-confidence abstention and log a diagnostic. DEFINITION OF DONE: boundary, cap, monotonicity, missing-data, and one-retry tests pass; repeated input produces byte-equivalent score components. (verified: `docs/Restaurant Implementation Plan.md` §§5–6; `product-req.pdf` pp. 7–8)

## Estimated Revenue-at-Risk Algorithm

Separate observed booked-value loss from projected revenue at risk:

```text
observed_cancelled_value = sum(amount for delivery cancellations in incident window)
excess_cancel_rate       = max(0, current_cancel_rate - baseline_cancel_rate)
projected_orders         = current_order_rate_per_minute * forecast_horizon_minutes
projected_revenue_at_risk = projected_orders * average_order_value * excess_cancel_rate
display_total_exposure    = observed_cancelled_value + projected_revenue_at_risk
```

CONFIG_DEFAULT forecast horizon is 60 minutes under A9. Use only same-currency orders; omit the estimate with `INSUFFICIENT_DATA` when average order value, rate denominators, or currency consistency is missing. Label the result “Estimated revenue exposure,” show horizon and inputs, and never claim profit loss or causal certainty. [assumed: transparent heuristic — if wrong: business-approved formula must replace it before presentation]

WHAT: provide a transparent magnitude estimate for prioritization. WHY: the PRD promises estimated revenue at risk, which the candidate omitted. INPUT: current/baseline cancellation metrics, order rate, average value, currency, horizon. OUTPUT: observed cancelled value, projected exposure, total, inputs, formula version. OWNER: Person 1. DEPENDENCIES: aggregation and restaurant currency. FAILURE BEHAVIOR: returns `INSUFFICIENT_DATA`, never zero, when inputs are invalid. DEFINITION OF DONE: unit/currency, zero-excess, missing-data, and fixture arithmetic tests pass; UI displays assumptions beside the estimate. (verified: `product-req.pdf` pp. 2, 11, 13)

## Recommendation Engine

The versioned `OPERATIONAL_OVERLOAD_V1` rule returns three advisory steps: temporarily reduce simulated incoming delivery load, increase displayed simulated preparation estimates, and prioritize the existing simulated queue. Expected impacts identify target metrics and direction, not guaranteed percentages. Risk tier is `MEDIUM`; expiry defaults to 15 minutes of demo event time. [assumed: recommendation rule/expiry — if wrong: product owner edits config/copy before M1]

WHAT: map a known evidence pattern to reviewed action text and target metrics. WHY: known patterns should not rely on generative selection. INPUT: incident type, evidence, confidence tier, simulator capabilities. OUTPUT: recommendation, urgency, risk tier, expiry, expected-impact specification, source `RULE`. OWNER: Person 1. DEPENDENCIES: incident and confidence. FAILURE BEHAVIOR: unknown pattern or low confidence yields no action and `MANAGER_REVIEW_REQUIRED`/`MONITOR_ONLY`. DEFINITION OF DONE: golden incident selects exactly one versioned rule; low confidence and unknown type never call an action. (verified: `docs/Restaurant Implementation Plan.md` §5)

## LLM Boundary

The `ExplanationProvider` receives only structured incident evidence, deterministic score/impact outputs, and an allowed vocabulary of uncertainty. It returns validated JSON containing `headline`, `probable_contributing_cause`, and `evidence_summary`; every number and source ID must match input. The provider does not select recommendations or alter state. A deterministic template is mandatory fallback. [assumed: provider contract — if wrong: only the adapter contract changes]

WHAT: produce concise manager-readable prose from verified fields. WHY: the PRD requires explanation, while deterministic code owns calculations and decisions. INPUT: redacted structured evidence. OUTPUT: grounded prose plus provider/model version or `TEMPLATE`. OWNER: Person 1. DEPENDENCIES: complete incident evidence and optional `${LLM_API_KEY}`. FAILURE BEHAVIOR: timeout, invalid JSON, unsupported claim, or absent credential immediately uses template and records the failure. DEFINITION OF DONE: mocked success, timeout, malformed, hallucinated-number, and no-key tests pass; every displayed claim traces to evidence. (verified: `docs/Restaurant Implementation Plan.md` §5; `product-req.pdf` pp. 13–14)

## LangGraph Role

LangGraph starts only after deterministic correlation creates/updates an incident candidate. Required state fields are incident ID, restaurant ID, window, evidence IDs, metric snapshot, confidence components, retry count, recommendation ID, approval decision, and status. Required nodes are `load_evidence`, parallel deterministic `specialist_*`, `correlate`, `score`, conditional `widen_once`, `estimate_impact`, `explain`, `recommend`, `persist`, `await_approval`, and `schedule_verification`. Node-visit ceiling and retry count are configuration. (user: Q5; verified: bounded-loop requirement in `product-req.pdf` pp. 6–8)

WHAT: make post-trigger investigation, bounded retry, and approval pause/resume explicit and observable. WHY: the accepted MVP must truthfully demonstrate agent orchestration without treating detectors as autonomous AI. INPUT: incident candidate ID. OUTPUT: persisted investigation/recommendation state and WebSocket transitions. OWNER: Person 1 graph; Person 2 checkpoint/persistence integration. DEPENDENCIES: deterministic functions and database. FAILURE BEHAVIOR: node failure persists `INVESTIGATION_FAILED`, emits a failure transition, and supports idempotent resume; the graph cannot loop beyond its ceiling. DEFINITION OF DONE: golden trace visits expected nodes, low-confidence trace widens once, crash resumes from checkpoint, and no raw event starts a graph. (user: Q5)

## Incident Lifecycle and Human Approval

```text
DETECTED → INVESTIGATING → MONITOR_ONLY
                       ↘ AWAITING_APPROVAL → ACTION_REJECTED
                                           → ACTION_APPROVED → VERIFYING
                                                              → RESOLVED
                                                              → NOT_IMPROVED
INVESTIGATING → INVESTIGATION_FAILED
```

All M1 actions are medium risk and require a manager decision; high confidence does not bypass approval. `EDIT` stores the suggested and edited action and then transitions as approval. Approval after expiry returns `409`; repeated requests with the same idempotency key return the original result. Simulator execution begins only after persisted approval and records success/failure. [assumed: lifecycle/expiry semantics — if wrong: API and graph transitions change]

WHAT: enforce auditable state transitions and prevent unapproved simulated action. WHY: human control and timestamps are explicit PRD requirements. INPUT: recommendation plus manager command. OUTPUT: action audit record, simulator command, next state. OWNER: Person 2 domain/API; Person 3 controls; Person 1 graph interrupt. DEPENDENCIES: recommendation and identity A8. FAILURE BEHAVIOR: invalid transition/expired recommendation returns `409`; simulator failure records `EXECUTION_FAILED` and does not start verification. DEFINITION OF DONE: transition matrix, audit timestamp, approve/reject/edit, expiry, duplicate command, and execution-failure tests pass. (verified: `product-req.pdf` pp. 8, 12)

## Outcome Verification

The recommendation stores target metrics, expected direction, and `check_after`. CONFIG_DEFAULT: compare the incident’s last complete pre-action 30-minute window with the first complete 30-minute window starting after simulated execution; normalize interpretation by order volume. Classification is `IMPROVED` when cancellation rate falls at least 20% and preparation mean does not worsen more than 10%; `WORSENED` when either primary metric worsens at least 15%; `NO_CHANGE` otherwise; fewer than 10 eligible orders returns `INSUFFICIENT_DATA`. [assumed: evaluation windows/thresholds — if wrong: outcome config changes]

`IMPROVED` resolves the incident. `NO_CHANGE` or `WORSENED` becomes `NOT_IMPROVED`; M1 stops there and does not automatically generate a second action, despite the PRD’s future re-investigation loop. [assumed: bounded demo scope — if wrong: a second hypothesis/action path adds graph, simulator, and UI scope]

WHAT: evaluate whether target metrics moved as expected after the simulated action. WHY: the closed loop is the product’s differentiator. INPUT: approved action, before/after metric windows, outcome rule version. OUTPUT: classification, raw metrics, deltas, quality, evaluation timestamps. OWNER: Person 1 rule, Person 2 scheduler/persistence, Person 3 comparison UI. DEPENDENCIES: action execution and enough post-action events. FAILURE BEHAVIOR: delayed/sparse data remains `INSUFFICIENT_DATA` and schedules one later check; rule error records verification failure without resolving. DEFINITION OF DONE: deterministic fixtures cover all four outcomes and the UI avoids causal wording. (verified: `product-req.pdf` pp. 8, 13–14)

## Simulator and Demo Timing

The repository stores a versioned scenario manifest and timestamped JSON fixtures. A seed controls IDs and numeric jitter. `speed` changes wall-clock delay only; event-time offsets and derived results remain constant. CONFIG_DEFAULT full demo event time: seven baseline days loaded without animation, 15 minutes healthy, 30 minutes surge, 20 minutes degradation/cancellations/reviews, approval pause, 30 minutes recovery, then verification. CONFIG_DEFAULT wall-clock target is 4–6 minutes at demo speed. [assumed: timing — if wrong: manifest config changes without algorithm edits]

The runner must call `POST /events` for every live event and may bulk-load baseline only through the same endpoint with animation suppressed. Demo reset may delete only records marked synthetic and tied to a scenario run. (verified: real ingestion path requirement in `product-req.pdf` p. 9; [assumed: reset safety — if wrong: reset remains disabled])

WHAT: reproduce the exact healthy→overload→action→recovery story. WHY: evaluation depends on repeatable inputs and a visible real pipeline. INPUT: scenario, seed, speed, API URL. OUTPUT: accepted events and scenario run status. OWNER: Person 2. DEPENDENCIES: event API and frozen config. FAILURE BEHAVIOR: failed post retries with the same event ID; reset refuses non-demo mode; run can resume from last accepted sequence. DEFINITION OF DONE: two clean runs with the same seed yield identical incidents, scores, impact, and outcome; a projector-visible run completes within configured wall time. (verified: reproducibility requirement in `product-req.pdf` p. 12)

## Frontend Experience

Routes are `/operations`, `/incidents/:id`, and `/incidents/:id/action`. Operations shows synthetic banner, restaurant health, active incident, headline metrics, and a live stage rail. Incident detail shows what happened, probable contributing cause, confidence components, source evidence, revenue estimate inputs, recommendation, and uncertainty. Action shows approve/reject/edit, execution status, and before/after outcome. [assumed: route structure — if wrong: frontend navigation changes only]

WHAT: make the decision loop understandable without implying unsupported capabilities. WHY: judges must see real ingestion-to-verification transitions. INPUT: REST state and WebSocket transition IDs. OUTPUT: accessible responsive screens with loading, empty, stale, reconnecting, error, expired-action, and insufficient-data states. OWNER: Person 3. DEPENDENCIES: OpenAPI fixtures and A7. FAILURE BEHAVIOR: WebSocket loss never erases REST state; unknown evidence fields are hidden with a diagnostic; action controls disable after terminal transitions. DEFINITION OF DONE: Playwright covers full golden flow and reconnect; all restaurant screens display the synthetic label; presentation copy uses “probable contributing cause” and “estimated exposure.” (verified: frontend requirements in `docs/Restaurant Implementation Plan.md` §13 and `product-req.pdf` pp. 9–11)

## Failure Handling and Landmine Adaptations

- PostgreSQL unavailable → health check fails; ingestion returns `503`; no acceptance is claimed. [assumed: fail-closed persistence — if wrong: data loss risk]
- Redis unavailable → durable outbox retains accepted events; UI reports processing delayed; recovery republishes. [assumed: outbox design — if wrong: remove resilience claim]
- Duplicate/out-of-order events → idempotency and event-time windows prevent duplicate incidents; excessive lateness is stored and flagged. [assumed: delivery semantics — if wrong: metrics can drift]
- LLM unavailable/unsupported output → deterministic explanation template. (verified: grounded LLM boundary requirement in `docs/Restaurant Implementation Plan.md` §5)
- WebSocket unavailable → REST refresh restores truth; live rail shows reconnecting. (user: Q4)
- Sparse baseline/evidence → abstain or `INSUFFICIENT_DATA`, never manufacture confidence or impact. (verified: `product-req.pdf` pp. 7–8)
- Demo reset could destroy real data → endpoint requires demo mode and synthetic scenario IDs; production configuration returns `404`. [assumed: safety adaptation — if wrong: do not ship reset]
- PRD claims memory-informed decisions → M1 presentation says outcomes are “stored for future retrieval,” not that current recommendations learn from them. [assumed: truthful scope adaptation — if wrong: seeded-memory implementation is required]
- Three independent branches could drift contracts → freeze JSON fixtures/OpenAPI before parallel work and require all three owners on contract changes. [assumed: collaboration control — if wrong: integration rework increases]

## Tests and Verification

Exact package commands are selected and documented in Phase 1 because no manifests or lockfiles exist. (verified: repository file scan)

Required suites are: pure unit tests for metrics/detectors/correlation/confidence/impact/recommendation/outcome; PostgreSQL and Redis integration tests for migrations, outbox, consumer replay, idempotency, and graph resume; OpenAPI/fixture contract tests; frontend component tests; Playwright golden demo and reconnect; and a Docker Compose smoke run. [assumed: testing tool choices except stack — if wrong: equivalent suites retain acceptance behaviors]

Success checks are:

- 100% of versioned golden lunch-rush runs create exactly one overload incident; normal and near-threshold fixtures create none. [assumed: scripted acceptance bar — if wrong: demo is nondeterministic]
- Detection-to-recommendation completes within 30 wall-clock seconds for the configured demo dataset, excluding approval wait. (verified: `product-req.pdf` p. 12)
- Every recommendation traces to stored signal and event IDs; every displayed number matches a deterministic persisted value. (verified: `product-req.pdf` pp. 12–13)
- Every medium-risk action requires approval and records decision/execution/outcome timestamps. (verified: `product-req.pdf` pp. 8, 12–13)
- A clean seeded run reaches `RESOLVED/IMPROVED`; failure fixtures visibly cover abstention, rejection, execution failure, and insufficient data. [assumed: acceptance scenarios — if wrong: definition of done weakens]

## Deployment and Configuration

CONFIG_DEFAULT A1: Docker Compose runs `frontend`, `backend`, `postgres`, `redis`, and one backend worker process on one demo machine. The scheduler runs in the worker; WebSocket fan-out uses backend process memory because only one backend replica exists. [assumed: topology — if wrong: pub/sub fan-out and distributed scheduling are required]

Configuration includes database/Redis URLs, CORS origin, demo-mode flag, LLM provider/key, LangGraph/LangSmith settings, all window/threshold/weight/retry/expiry/outcome values, and scenario speed. Commit `.env.example` without secrets and version the demo config. (verified: PRD stack; [assumed: configuration inventory — if wrong: missing variables are added before M0])

WHAT: provide one-command reproducible local/judged runtime. WHY: Redis, PostgreSQL, worker, WebSocket, and frontend must operate together. INPUT: environment variables and images. OUTPUT: health-checked services and demo URL. OWNER: Person 2, with Person 3 frontend image. DEPENDENCIES: A1–A2. FAILURE BEHAVIOR: startup fails on missing required config and reports unhealthy dependencies. DEFINITION OF DONE: a clean machine follows `docs/demo/RUNBOOK.md`, starts the stack, resets synthetic data, and completes the golden scenario without source edits. [assumed: one-command target — if wrong: runbook must name exact hosted steps]

## Observability

Structured logs carry request ID, stream message ID, scenario run, restaurant, window, incident, graph run, and action IDs. Metrics cover accepted/rejected/duplicate events, outbox backlog, Redis pending count, processing latency, detector firings, dedup updates, graph node duration/failures, WebSocket connections, LLM fallback, approval latency, and outcome counts. WebSocket stage messages mirror persisted stage changes but are not the audit log. [assumed: telemetry set — if wrong: debugging/presentation visibility degrades]

WHAT: trace a demo incident end to end and expose stalled processing. WHY: asynchronous handoffs otherwise hide failure location. INPUT: stage lifecycle events. OUTPUT: structured local logs, health/readiness endpoints, metrics, and optional LangSmith trace under A10. OWNER: Person 2 platform; Person 1 graph spans; Person 3 visible stage rail. DEPENDENCIES: shared correlation IDs. FAILURE BEHAVIOR: remote tracing failure never blocks processing. DEFINITION OF DONE: one incident can be reconstructed from logs by `scenario_run_id`, and deliberate Redis/LLM/WebSocket failures are distinguishable. (verified: tracing requirement in `product-req.pdf` pp. 10–12)

## Three-Person Ownership and Dependency Graph

- Person 1 — Intelligence/graph: metric contracts, aggregation, baselines, five detectors, correlation, confidence, impact, recommendation, explanation boundary, LangGraph, outcome rules. (verified: `docs/Restaurant Implementation Plan.md` §14, refined by frozen MVP)
- Person 2 — Backend/platform/simulator: tooling, migrations, event API, outbox/Redis consumer, persistence, lifecycle, REST/WebSocket, scheduler, simulator, Docker, logs. (verified: `docs/Restaurant Implementation Plan.md` §14, refined by frozen MVP)
- Person 3 — Frontend/demo: OpenAPI client, fixtures, three routes, stage rail/WebSocket recovery, evidence/impact views, approval/outcome states, accessibility, demo runbook/rehearsal. (verified: `docs/Restaurant Implementation Plan.md` §14, refined by frozen MVP)

```text
versioned contracts + golden fixtures
├─ Person 1: pure intelligence functions ─┐
├─ Person 2: ingestion/storage/stream ────┼─ M0 integration
└─ Person 3: fixture-driven UI ───────────┘
                 ↓
signals → incident → REST detail → rendered evidence
                 ↓
LangGraph → recommendation → approval → simulator recovery
                 ↓
outcome → WebSocket transition → before/after UI → M1
```

Contract files are the integration boundary; after Phase 1, envelope/incident/action changes require all three owners. [assumed: review rule — if wrong: contract drift risk rises]

## M0 Vertical Slice

M0 uses one `order.cancelled` event fixture and a deliberately simple fixture-backed cancellation baseline. It must travel through the real API, PostgreSQL outbox, Redis consumer, one deterministic detector, persisted signal/incident, REST incident detail, WebSocket stage notification, and frontend incident card. LangGraph may contain only load/persist nodes in M0 but must be the path used. [assumed: thinnest real slice — if wrong: M0 expands and delays integration]

M0 is done when a clean Docker Compose run demonstrates that path, duplicate delivery creates no duplicate incident, browser reconnect restores state through REST, and all three developers can run the same automated smoke test. (user: Redis/WebSocket/LangGraph decisions; verified: vertical slice requirement in `docs/Restaurant Implementation Plan.md` §15)

## M1 Full Scenario

M1 loads baseline events, streams healthy lunch service, injects volume/preparation/handoff/cancellation/review degradation, creates exactly one overload incident, shows specialist-node transitions, computes confidence and revenue exposure, displays grounded explanation and rule recommendation, pauses for approve/reject/edit, changes simulator behavior after approval, streams recovery, verifies outcome, and stores `IMPROVED/RESOLVED`. (user: Q2–Q5; verified: closed-loop requirement in `product-req.pdf` pp. 8–9)

M1 is done only when the same seed produces the same stored evidence, score, estimate, recommendation, and outcome twice from a clean reset; normal and low-evidence runs demonstrate no incident and abstention respectively. [assumed: reproducibility bar — if wrong: presentation cannot make deterministic claims]

## Final Build Order

- [ ] Phase 1: Freeze executable contracts and prove the runtime

  Done when: lockfiles/config are committed; Docker services are healthy; canonical fixtures validate in Python and TypeScript; Redis crash/reclaim spike and LangGraph checkpoint spike pass. [assumed: Phase 1 checks — if wrong: downstream choices remain unsafe]

  Steps: select compatible versions from current official package metadata; create decision/config ledgers; scaffold packages; create `.env.example`; define OpenAPI/event/incident fixtures; prove PostgreSQL, Redis consumer recovery, WebSocket reconnect, and LangGraph persistence in thin spikes; record fallbacks for A1–A10.

  Covers: contracts, technology, deployment; checks A1–A10.

- [ ] Phase 2: Build and calibrate deterministic scenario math

  Done when: golden normal/surge fixtures produce reviewed metric snapshots, detector signals, confidence components, and impact arithmetic; numeric values live only in versioned config. (user: numeric-default discipline)

  Steps: build baseline simulator data; implement windows/baselines; write failing detector boundary tests; implement detectors/correlation/confidence/impact/recommendation/outcome; publish a calibration report with normal, positive, and near-threshold results.

  Covers: aggregation through outcome algorithms; checks A3–A5 and A9.

- [ ] Phase 3: Deliver M0 through the real infrastructure

  Done when: the M0 acceptance paragraph passes from clean Compose startup. (verified: M0 above)

  Steps: migrate core tables; implement event/outbox transaction; publish/consume `restaurant.events`; persist one signal/incident; implement minimal LangGraph path; expose incident REST/WebSocket; connect frontend card; test replay/reconnect.

  Covers: ingestion, streaming, persistence, first UI.

- [ ] Phase 4: Complete multi-signal investigation

  Done when: the full degradation fixture produces one deduplicated incident with traceable evidence, one bounded retry path, explanation fallback, confidence, and impact. [assumed: investigation acceptance — if wrong: M1 cannot proceed]

  Steps: add all detectors; implement correlation/dedup; complete LangGraph nodes/checkpointing; add score/impact; add explanation provider/template; broadcast transitions; test crashes and abstention.

  Covers: detection through investigation.

- [ ] Phase 5: Complete recommendation, approval, and simulated execution

  Done when: approve/reject/edit/expiry/idempotency tests pass and only approval changes simulator behavior. (verified: approval requirement in `product-req.pdf` p. 8)

  Steps: implement rule engine; add graph interrupt/resume; add decision endpoint; add audit records; wire simulator control; build action UI states; test execution failure.

  Covers: recommendation and approval.

- [ ] Phase 6: Close the outcome loop

  Done when: all four outcome fixtures pass and the approved golden run becomes `IMPROVED/RESOLVED` with visible raw before/after metrics. [assumed: outcome acceptance — if wrong: closed loop is incomplete]

  Steps: implement scheduler; persist check targets; compute post window; classify outcome; emit transition; build comparison UI; test retry and insufficient data.

  Covers: verification and incident terminal states.

- [ ] Phase 7: Harden and rehearse M1

  Done when: clean-machine runbook completes two identical 4–6 minute runs; CI passes; deliberate dependency failures show specified behavior; presentation claims checklist contains no unsupported capability. [assumed: demo duration — if wrong: speed config and runbook change]

  Steps: finish health/metrics/logging; add Playwright golden flow; test reset guard; verify synthetic labels and causal wording; measure under-30-second detection-to-recommendation latency; rehearse projector layout; capture fallback recording/log bundle.

  Covers: M1, deployment, observability, presentation integrity.

## Definition of Done

- Frozen M1 scope and all non-goals are reflected in code, runbook, and presentation. (user: Q2–Q5)
- A clean seeded lunch-rush demo traverses the real API, PostgreSQL, Redis, deterministic detection, LangGraph, WebSocket, approval, simulator, and outcome path. (user: Q2–Q5)
- All calculations are deterministic, versioned, tested, and visible; the LLM produces prose only and has a template fallback. (verified: `docs/Restaurant Implementation Plan.md` §5)
- Numeric rules are identified as configurable defaults and the frozen demo configuration has a calibration report. (user)
- Duplicate, late, sparse, disconnected, dependency-failure, low-confidence, rejected, and failed-action paths behave as specified. [assumed: executor completeness bar — if wrong: named risks remain]
- The UI labels synthetic data, distinguishes estimated exposure from realized cancelled value, and makes no absolute-causality or learned-memory claim. (verified: source requirements and red-team findings above)
- CI and the clean-machine runbook prove M0 and M1 without unstated credentials; optional remote services degrade safely. [assumed: handoff bar — if wrong: executor cannot reproduce]

## Architecture Decisions Now Frozen

- The MVP is a modular monolith with separate frontend and simulator processes, not microservices. (verified: `docs/Restaurant Implementation Plan.md` §§9, 18)
- The single M1 story is lunch-rush operational overload using POS, KDS preparation, delivery, and review events. (user: Q2)
- FastAPI validates canonical events; PostgreSQL is durable truth; Redis Stream `restaurant.events` is the mandatory asynchronous event handoff. (user: Q3; verified: PRD stack)
- Processing is at-least-once and domain writes must be idempotent; Redis and WebSocket are not authoritative storage. [assumed: required reliability consequence of Q3/Q4 — if wrong: delivery guarantees must be re-decided]
- Deterministic detection creates incident candidates before LangGraph starts. (user: Q5)
- LangGraph is mandatory for post-detection orchestration, one bounded widening retry, approval pause/resume, and verification scheduling; it is never invoked per routine event. (user: Q5)
- REST is authoritative UI state; one WebSocket channel carries transient live pipeline transitions. (user: Q4)
- Confidence, severity, revenue impact, correlation, recommendation selection, and outcome classification are deterministic and versioned; LLM use is grounded prose only. (verified: `docs/Restaurant Implementation Plan.md` §5)
- Every consequential M1 action requires human approval and affects only the simulator. (verified: `product-req.pdf` p. 8)
- Outcomes are stored and shown, but M1 does not claim causal proof or memory-informed learning. [assumed: truthful scope boundary — if wrong: M1 scope expands]
- All thresholds, weights, window lengths, baseline lookback, lateness, retry ceilings, expiry, forecast horizon, and outcome deltas are configuration defaults, not product facts. (user)
- The default deployment is one-machine Docker Compose and must be validated before downstream implementation. [assumed: A1 — if wrong: architecture must be revised in Phase 1]

## Deferred Decisions

- Real source connectors, production throughput, horizontal scaling, multi-region operation, and service extraction must not influence MVP topology. [assumed: no evidence of production load — if wrong: provide measured load/hosting constraints before architecture]
- Weather, payment, inventory, staffing, refund, stockout, and alternate demo scenarios must not add schemas or detectors to M1. (user: Q2; verified: explicit single-scenario planning constraint)
- Vector databases, embeddings, fine-tuning, AI Copilot, and memory-weighted recommendations must not influence MVP storage. (verified: structured memory preference in `product-req.pdf` p. 7; [assumed: Copilot deferred — if wrong: retrieval scope expands])
- External notifications and real operational execution must not influence MVP integrations. (verified: hackathon non-goals in `product-req.pdf` pp. 3, 8)
- Production authentication, authorization, tenancy, compliance, retention, backup, disaster recovery, and SLO topology remain future decisions; demo reset must stay isolated meanwhile. [assumed: hackathon deployment — if wrong: security architecture must precede implementation]
- Broad analytics, global timeline, learned confidence recalibration, and automatic re-investigation after a failed action are deferred and must not expand M1 APIs beyond the narrow summary. [assumed: demo-value prioritization — if wrong: timeline/analytics/loop become new milestones]
- Exact dependency versions, frontend build tool, scheduler library, LLM provider/model, and hosted platform remain Phase 1 selections constrained by the frozen boundaries above. (verified: no manifests/lockfiles in repository; PRD names candidates but not verified versions)

The Assumptions Ledger is the complete list of defaults adopted without a user decision; every one has an early verification or fallback so an executor does not need this conversation. (verified: completeness and executor gates applied to this document)
