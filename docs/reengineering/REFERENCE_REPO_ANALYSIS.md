# Reference Repository Analysis

Reference: [`caleb-andersen/hackerrank-orchestrate-august26/code`](https://github.com/caleb-andersen/hackerrank-orchestrate-august26/tree/main/code)

Analysis date: 2026-08-09

## Executive finding

The reference repository is a bounded message-routing agent, not a forecasting architecture. Its reusable contribution to LOSSLine is the control system around model judgment: deterministic context construction, strict typed submission, limited tool use, post-model guards, traceability, label isolation, and explicit evaluation. Its use of an LLM as the primary classifier must not be copied for restaurant demand forecasting.

## 1. Data ingestion model

`data/loader.py` reads a fixed set of CSV tables into frozen, slotted dataclasses from `data/schema.py`. Parsing, referential validation, timestamp handling, and allowed categorical values happen before routing. A `Dataset` is loaded once and passed explicitly; the decision path does not query mutable global state.

LOSSLine adaptation: retain raw source payloads for audit, normalize them into typed observations, and construct point-in-time snapshots from PostgreSQL. Do not copy the batch-CSV boundary as the production architecture.

## 2. Feature and context computation

`context/index.py` builds deterministic lookup indexes once. `context/features.py` and `context/retrieval.py` compute rates, counts, relationship state, repetition, timing, risk indicators, and ranked evidence before any model call. Zero-denominator rates are `None`, and the associated sample counts are carried alongside them.

The context package is designed as pure, acyclic code. It performs no network calls, clock reads, random operations, prompt construction, or filesystem writes.

LOSSLine adaptation: build point-in-time feature snapshots using explicit `prediction_as_of`; carry missingness, denominators, freshness, provenance, and data sufficiency into every forecast dossier.

## 3. Dossier structure

The reference `Dossier` is a frozen, slotted dataclass composed of typed sections:

- sender identity;
- relationship and engagement history;
- content-derived signals;
- repetition and near-duplicate history;
- ranked evidence candidates;
- media state;
- timing context.

The model receives curated facts instead of CSV rows. Untrusted source text is fenced as data when rendered into a prompt.

LOSSLine adaptation: create a `ForecastDossier` from typed persisted forecast, inventory, capacity, risk, attribution, historical-performance, constraint, and retrieval artifacts. It must not contain raw database tables, event dumps, or provider payloads.

## 4. Agent state

The reference loop holds one dossier, provider/model state, messages, tool counters, validation failures, usage metrics, and terminal outcome. State is scoped to one message-routing decision. Checkpoint fingerprints include relevant inputs and versions so stale results are not silently reused.

LOSSLine adaptation: use durable `OperationalInvestigationState` containing immutable artifact references and an explicit retry count, guard result, approval state, and outcome state.

## 5. Tools

The agent has a small declared tool surface. Media inspection tools are bounded separately, and `submit_routing_decision` is the only terminal decision mechanism. Unknown tools and exhausted budgets return explicit failures.

LOSSLine adaptation: expose bounded, read-only tools for persisted forecasts, projections, drivers, precedents, and SOPs, plus exactly one strict `submit_operational_decision` tool. Media tools are not relevant to numerical prediction.

## 6. Routing and decision mechanism

The model judges independent risk, relevance, and urgency axes. A deterministic precedence table resolves those axes to `notify`, `digest`, or `mute`. This makes judgment inspectable and allows downstream validation to compare the proposed action with its stated factors.

LOSSLine adaptation: keep risk type, urgency, action risk, decision-support strength, and approval requirements distinct. Numerical risk candidates are computed before the agent; the agent selects among valid responses or abstains.

## 7. Typed decision output

The agent must call `submit_routing_decision` with enum-constrained fields, bounded confidence, evidence IDs, and a reason. `guards/validate.py` validates shape, vocabulary, reason style, evidence references, and cross-field invariants. Arbitrary prose is not accepted as a production decision.

LOSSLine adaptation: validate a `DecisionCandidate` containing artifact references, action enum, optional quantity and unit, evidence IDs, urgency, action risk, approval requirement, and decision version.

## 8. Deterministic guards

`guards/safety_gate.py` applies a zero-model-call safety gate after validation. It handles injection, credential requests, impersonation, payment pressure, opt-out state, behavioural demotion, and media mismatch. The gate is one-directional: it may only move an action toward the safer result and lower confidence. An assertion enforces that property.

LOSSLine adaptation: guards may reject, reduce quantity/scope, require approval, or abstain. They must never increase action quantity, urgency, autonomy, or operational exposure.

## 9. Confidence handling

The model supplies raw confidence, after which code clamps and penalizes it under defined conditions. The evaluation package calculates confidence error and reliability bins. This is more disciplined than displaying an unchecked number, but the raw score still originates with the model and is specific to the competition output contract.

LOSSLine adaptation: do not let the LLM generate forecast confidence. Keep forecast intervals, historical accuracy, data quality, operational risk, and decision-support strength separate. Publish numeric confidence only after calibration.

## 10. Evaluation harness

`evaluation/main.py` runs labelled samples, validates output shape, computes metrics, performs a full-output consistency audit, and optionally evaluates reason quality. `evaluation/metrics.py` reports action/type accuracy, confusion matrices, catastrophic errors, evidence precision/recall/F1, confidence error, and reliability bins. The final composite score does not replace the component reports.

LOSSLine adaptation: maintain separate forecast, risk, agent, guard, explanation, and consistency reports. A composite score must never hide a failed safety or subgroup gate.

## 11. Labelled-data usage

Gold labels are loaded only inside `evaluation/records.py` and the rule-only evaluation baseline. Production loading and routing receive message inputs with the label fields removed. This creates an observable anti-leakage boundary.

LOSSLine adaptation: actual demand and golden expected decisions must live behind evaluation boundaries. Training targets may enter model training, but never feature construction or live dossier assembly.

## 12. Consistency testing

`evaluation/consistency.py` clusters near-duplicate messages, compares their actions, and distinguishes explainable divergence caused by personalization features from unexplained inconsistency. Tests also cover validation, client failure policy, feature computation, media handling, injection, safety gating, and evaluation.

LOSSLine adaptation: repeat identical dossiers, compare scenario-equivalent cases, and require any decision divergence to trace to a changed forecast, constraint, risk, retrieved policy, or approved stochastic setting.

## 13–14. Pattern disposition

| Pattern | Reference implementation | Why it exists | Suitable for LOSSLine? | Adaptation |
|---|---|---|---|---|
| Typed ingestion | Frozen CSV row dataclasses | Stable input semantics | Yes | Typed raw events and normalized observations |
| Deterministic feature index | Precomputed joins/history indexes | Reproducibility and speed | Yes | Point-in-time outlet/SKU/window snapshot index |
| Computed dossier | Frozen structured context | Prevent raw-data reasoning | Yes | `ForecastDossier` of persisted computed artifacts |
| Explicit missingness | `None` rates plus sample counts | Avoid false zero evidence | Yes | Missing, stale, censored and imputed states |
| Bounded tools | Maximum loop and media calls | Prevent unbounded behavior | Yes | Fixed context-call budget and one repair |
| Strict submission | `submit_routing_decision` | Prevent prose becoming action | Yes | `submit_operational_decision` |
| Cross-field validation | Schema plus invariants | Detect incoherent decisions | Yes | Validate grain, references, units and policy |
| One-directional guard | Gate only demotes action/confidence | Enforce safety outside model | Yes | Reject/restrict/require approval; never expand |
| Decision tracing | Metrics, checkpoint and trace data | Audit and resume | Yes | Persist dossier-to-outcome trace |
| Label isolation | Evaluation-only gold loader | Prevent leakage | Yes | Separate actuals/golden labels from inference |
| Consistency audit | Near-duplicate divergence analysis | Detect instability | Yes | Repeatability and equivalent-scenario audits |
| Confidence bins | Reliability evaluation | Detect overconfidence | Yes | Calibrate decision support and interval coverage |
| LLM primary classifier | Model owns routing judgment | Semantic classification task | No | Evaluated statistical model owns demand forecast |
| Model-proposed confidence | Required output field | Competition contract | No | Derive metrics outside the LLM |
| Prompt policy engine | Large routing rubric | Express semantic routing policy | Mostly no | Put operational formulas and limits in code |
| Multimodal tools | OCR/ASR/image inspection | Message attachments | Not initially | Optional SOP ingestion only, never forecasting |
| CSV writer/checkpoints | Batch submission requirement | Competition delivery format | No | PostgreSQL artifacts and durable graph checkpoints |

## Sources inspected

- `code/README.md`
- `code/SPEC_features.md`
- `code/data/loader.py`, `code/data/schema.py`
- `code/context/features.py`, `index.py`, `retrieval.py`, `scanners.py`
- `code/agent/loop.py`, `prompts.py`, `tools.py`, `client.py`
- `code/guards/validate.py`, `decision.py`, `safety_gate.py`, `reason_repair.py`
- `code/evaluation/main.py`, `metrics.py`, `records.py`, `consistency.py`, `baseline.py`
- `code/tests/`

