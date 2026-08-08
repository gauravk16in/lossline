# LOSSLine — Implementation Planning Prompt

You are a senior software architect and backend engineer helping us plan **LOSSLine**, a restaurant operational intelligence system.

Your task is **NOT to write code yet**.

First, study the project context below and then produce a detailed, practical **implementation plan** that a 3-person team can execute quickly. After the implementation plan is finalized, we will create the final system architecture from it.

---

## 1. Project Goal

LOSSLine helps restaurant operators answer:

1. **What happened?**
2. **Why did it happen?**
3. **What should we do now?**
4. **Did the action improve the result?**

The system should ingest operational events from a restaurant outlet, detect unusual patterns, correlate signals from multiple sources, identify a probable operational cause, recommend an action, and later measure whether the action improved the situation.

This is not meant to be another analytics dashboard.

The core value is:

> **Operational signals → anomaly → evidence correlation → probable cause → recommended action → manager decision → outcome verification**

---

## 2. MVP Demo Context

For the hackathon MVP, we do not have access to real restaurant internal systems.

We will therefore use a **synthetic restaurant event simulator**.

The demo restaurant can be represented as a multi-location restaurant business such as:

- Outlet A
- Outlet B
- Outlet C

All restaurant-specific metrics shown in the demo must be clearly marked as:

> **Synthetic data for demonstration**

The architecture should still be designed so real POS, inventory, review, delivery, staffing, and external APIs could replace the simulator later.

---

## 3. Primary Demo Scenario

Build the MVP around ONE scenario first.

### Lunch Rush → Operational Overload → Cancellations

Normal state:

- stable order volume
- normal preparation time
- low cancellation rate
- normal review sentiment

Then simulate:

1. lunch demand increases
2. order velocity exceeds historical baseline
3. preparation time increases
4. delivery handoff / waiting time increases
5. cancellation rate increases
6. negative reviews mentioning delay start appearing

LOSSLine should correlate these signals and produce something like:

```text
Incident:
Delivery cancellations increased significantly

Probable contributing cause:
Operational capacity mismatch during lunch demand spike

Confidence:
0.87

Evidence:
- order volume +38%
- preparation time +61%
- cancellation rate increased
- multiple complaints mentioning delay

Recommended action:
Temporarily reduce incoming delivery load,
increase preparation estimates,
and prioritize the existing order queue.
```

Important:

Do NOT claim absolute causal certainty.

Use language such as:

- probable cause
- likely contributing cause
- evidence-supported explanation

---

## 4. Desired End-to-End Flow

```text
Synthetic Event Generator
        ↓
POST /events
        ↓
Schema Validation + Normalization
        ↓
Event Store
        ↓
Window Aggregation / Baseline Comparison
        ↓
Parallel Specialist Detection Nodes
        ↓
Shared Evidence State
        ↓
Correlation Engine
        ↓
Deterministic Confidence Scoring
        ↓
Evidence-Grounded Explanation
        ↓
Recommendation Engine
        ↓
Incident Persistence
        ↓
Dashboard
        ↓
Manager Approves / Rejects / Edits Action
        ↓
More Events Arrive
        ↓
Outcome Verification
```

---

## 5. Important Architectural Rules

### Rule 1 — Do not make everything an AI agent

The specialist components should primarily be deterministic Python / SQL / statistical logic.

Examples:

- sales anomaly detector
- cancellation detector
- inventory risk detector
- preparation-time detector
- review issue detector
- external context detector

LangGraph may orchestrate these nodes, but do not pretend every detector is an autonomous AI agent.

### Rule 2 — LLM must not calculate confidence

Confidence must be deterministic and explainable.

It can consider:

- anomaly severity
- number of independent evidence sources
- temporal alignment
- historical similarity
- data quality

Keep confidence capped between `0` and `0.95`.

### Rule 3 — LLM is used for grounded explanation

The LLM receives structured evidence and produces a concise manager-readable explanation.

It must not invent unsupported causes.

Use a provider-agnostic interface.

### Rule 4 — Recommendation should be rule-first

For known incident patterns:

```text
incident pattern
→ deterministic recommendation lookup
```

Only use the LLM as fallback when the combination is not covered.

Recommendations remain advisory.

### Rule 5 — No infinite confidence loop

If confidence is low:

```text
initial analysis window → 2 hours

if confidence < 0.5:
    retry using wider context

if confidence is still < 0.5:
    mark incident as unresolved / insufficient evidence
```

Do not repeatedly search until the system manufactures a cause.

---

## 6. Decision Levels

Start with:

```text
0.00–0.49
Insufficient evidence / monitor

0.50–0.74
Manager review recommended

0.75–0.95
High-confidence operational alert
```

Severity should also affect priority.

Possible formula:

```text
priority = severity × confidence × estimated_business_impact
```

---

## 7. Core Event Schema

All components must use the SAME event contract.

Initial proposal:

```json
{
  "event_id": "evt_001",
  "outlet_id": "outlet_01",
  "source_type": "pos",
  "event_type": "order.completed",
  "timestamp": "2026-08-08T13:10:00Z",
  "payload": {}
}
```

Improve this if required, but keep one shared contract.

---

## 8. MVP Data Sources

MVP:

- POS / order events
- cancellation / refund events
- preparation-time events
- inventory events
- review / sentiment events
- weather / local context events

Phase 2:

- staffing
- delivery partner signals
- kitchen telemetry
- reservation data
- promotions
- local events

Clearly separate MVP from Phase 2.

---

## 9. Preferred Stack

Possible stack:

- FastAPI
- Python
- PostgreSQL
- LangGraph
- Pydantic
- SQLAlchemy or equivalent
- provider-agnostic LLM API
- LangSmith or Langfuse

Avoid unnecessary infrastructure.

Do not introduce Kafka, Kubernetes, microservices, vector databases, Redis, etc. unless there is a concrete MVP need.

Prefer a modular monolith.

---

## 10. Core APIs

Initial candidate endpoints:

```text
POST /events
GET /outlets
GET /incidents
GET /incidents/{incident_id}
POST /incidents/{incident_id}/actions
POST /incidents/{incident_id}/approve
POST /incidents/{incident_id}/reject
GET /incidents/{incident_id}/outcome
```

Define request/response responsibility for each.

---

## 11. Data Model

At minimum consider:

### events

```text
event_id
outlet_id
source_type
event_type
timestamp
payload
created_at
```

### signals

```text
signal_id
outlet_id
signal_type
severity
value
baseline
deviation
window_start
window_end
metadata
```

### incidents

```text
incident_id
outlet_id
status
severity
confidence
probable_cause
root_cause_explanation
created_at
window_start
window_end
rule_version
model_version
```

### incident_signals

Links incidents to supporting signals.

### recommendations

```text
recommendation_id
incident_id
action_text
urgency
expected_impact
source
```

Where source is:

```text
RULE
LLM_FALLBACK
```

### action_outcomes

```text
incident_id
manager_decision
action_taken
action_timestamp
metric_before
metric_after
resolved_status
manager_feedback
```

Improve schemas where needed.

---

## 12. Intelligence Pipeline

The implementation plan must explain how each stage is built.

### A. Event normalization

Raw event → validated normalized event.

### B. Window aggregation

Examples:

```text
orders/min
orders/hour
cancellation rate
average prep time
inventory depletion rate
review sentiment frequency
```

### C. Baseline calculation

For MVP use simple historical baselines.

Example:

```text
current 30-minute window
vs
comparable historical windows
```

Do not introduce unnecessary ML.

### D. Specialist detectors

Examples:

```text
ORDER_VOLUME_SPIKE
ORDER_DROP
CANCELLATION_SPIKE
PREP_TIME_SPIKE
REFUND_SPIKE
STOCKOUT_RISK
SENTIMENT_DROP
NEGATIVE_KEYWORD_SPIKE
EXTERNAL_DEMAND_CONTEXT
```

Each detector returns a structured `Signal`.

### E. Correlation

Signals close in outlet and time are grouped.

Example:

```text
ORDER_VOLUME_SPIKE
+
PREP_TIME_SPIKE
+
CANCELLATION_SPIKE
+
DELAY_REVIEW_SPIKE
```

can produce a candidate incident.

### F. Confidence

Use deterministic scoring.

Explain the algorithm clearly.

### G. Explanation

LLM converts structured evidence into manager-readable language.

### H. Recommendation

Rule lookup first.

LLM fallback second.

### I. Outcome verification

Compare relevant metrics before vs after intervention and return:

```text
IMPROVED
UNCHANGED
WORSENED
INSUFFICIENT_DATA
```

---

## 13. Frontend MVP

Do NOT build a generic BI dashboard.

Build only what communicates the decision loop.

### Screen 1 — Outlet Health

Show:

- outlet
- health state
- active incidents
- a few important metrics

### Screen 2 — Incident Investigation

Show:

```text
What happened?
Why LOSSLine thinks it happened
Confidence
Supporting evidence
Estimated impact
Recommended action
```

### Screen 3 — Action + Outcome

Show:

```text
recommended action
approve
reject
edit

then:

before vs after metrics
system assessment:
IMPROVED / UNCHANGED / WORSENED
```

---

## 14. Team Ownership

We have exactly **3 developers**.

### Person 1 — Intelligence + Integration

Owns:

- window aggregation
- baseline logic
- specialist detectors
- signal schema
- correlation
- confidence scoring
- recommendation rules
- LLM explanation integration
- end-to-end intelligence flow

### Person 2 — Backend + Simulator

Owns:

- FastAPI
- PostgreSQL
- event ingestion
- database models
- incident APIs
- action APIs
- synthetic event generator
- demo scenario scripts

### Person 3 — Frontend + Demo Experience

Owns:

- dashboard
- outlet view
- incident investigation
- evidence UI
- recommendation UI
- approval/rejection
- outcome comparison
- live polling / updates

All 3 must agree on shared contracts before coding.

---

## 15. First Engineering Milestone

# M0 — End-to-End Vertical Slice

Definition of done:

```text
Simulator generates one event
        ↓
POST /events accepts it
        ↓
event is stored
        ↓
one deterministic detector identifies anomaly
        ↓
one signal is generated
        ↓
one incident is created
        ↓
GET /incidents exposes it
        ↓
frontend displays the incident
```

Do NOT build multiple detectors before M0 works.

---

## 16. Second Milestone

# M1 — Complete Lunch Rush Scenario

Definition of done:

```text
healthy restaurant state
↓
synthetic demand spike
↓
prep-time degradation
↓
cancellation spike
↓
negative review signal
↓
multiple detectors fire
↓
signals correlate
↓
confidence calculated
↓
probable cause generated
↓
recommendation shown
↓
manager approves
↓
simulator generates recovery
↓
LOSSLine compares before vs after
↓
outcome shown
```

---

## 17. Output Required From You

Produce a detailed **IMPLEMENTATION_PLAN.md**.

Do not generate production code yet.

Organize it into:

1. MVP scope
2. assumptions
3. non-goals
4. proposed repository structure
5. core data contracts
6. database schema
7. API contracts
8. event ingestion flow
9. aggregation + baseline logic
10. specialist detector implementation
11. signal format
12. correlation algorithm
13. deterministic confidence algorithm
14. incident lifecycle
15. LLM explanation layer
16. recommendation engine
17. manager approval flow
18. outcome verification
19. synthetic-data generator
20. frontend integration
21. LangGraph state and nodes
22. error handling
23. observability / tracing
24. test strategy
25. security considerations
26. three-person ownership
27. dependencies between teammates
28. milestone-by-milestone execution order
29. exact first tasks for each teammate
30. MVP completion checklist

For every major section:

- explain what to build
- explain why it exists
- identify who owns it
- identify prerequisites
- give a definition of done

---

## 18. Planning Constraints

Keep the implementation realistic for a hackathon.

Prefer:

```text
simple > clever
deterministic > unnecessary AI
modular monolith > distributed services
rule-based MVP > premature ML
working vertical slice > many unfinished features
```

Do not overengineer.

Mark features clearly as:

```text
MVP
SHOULD HAVE
PHASE 2
```

If you identify a flaw in the proposed design, point it out rather than silently following it.

---

## 19. Final Required Sections

End the implementation plan with:

### A. Build Order

A numbered sequence showing exactly what should be implemented first, second, third, etc.

### B. Parallel Team Board

Use:

```text
Stage | Person 1 | Person 2 | Person 3 | Integration Check
```

### C. Architecture Inputs

List all decisions that will later be needed to create the final `ARCHITECTURE.md`.

Do **not** write the final architecture yet.

The architecture should be derived from the finalized implementation plan.
