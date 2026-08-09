# LOSSLine Hackathon Fix Plan

## 1. Goal

Deliver one reliable, honest, fully integrated lunch-rush demonstration:

```text
Synthetic events
→ FastAPI ingestion
→ PostgreSQL outbox
→ Redis Stream
→ deterministic detection and correlation
→ LangGraph investigation
→ one overload incident
→ manager approval
→ simulated recovery
→ improved outcome
→ resolved incident
```

The demo is successful only when the same seeded run produces the same result three consecutive times.

## 2. Desired Output

For the canonical `meghana_lunch_rush_v1` scenario, the system must produce:

- exactly one `OPERATIONAL_OVERLOAD` incident;
- status `AWAITING_APPROVAL` after degradation is processed;
- the required order-volume, preparation-time, and cancellation signals;
- optional handoff-delay and delay-review signals when supporting events exist;
- a deterministic confidence score and estimated revenue exposure;
- one non-expired recommendation;
- a grounded explanation marked as either `LLM` or `TEMPLATE`;
- status `ACTION_APPROVED` after manager approval;
- outcome `IMPROVED` after recovery data is processed;
- final incident status `RESOLVED`;
- no duplicate incidents, pending Redis messages, or DLQ messages.

## 3. Scope

### Included

- One canonical simulator scenario and runner.
- Existing FastAPI, PostgreSQL, Redis Streams, intelligence package, LangGraph workflow, and Vite React UI.
- Deterministic calculations and recommendations.
- Optional LLM-generated grounded explanation with template fallback.
- Manager approval and deterministic outcome verification.
- Tests and a repeatable demo smoke check.

### Not included

- New agents, detectors, dashboards, or demo scenarios.
- Real POS/KDS integrations or real-world action execution.
- Microservices, Kubernetes, authentication, multi-tenancy, or large refactors.
- Vector databases, RAG, conversational copilots, or autonomous recommendations.
- Production-scale Redis and WebSocket architecture.

## 4. Implementation Phases

### Phase 1 — Establish one canonical demo path

1. Treat `simulator/lossline_simulator/scenarios/lunch_rush.py` as the only presentation scenario.
2. Treat the Vite application under `apps/frontend/src/` as the only presentation UI.
3. Keep old M0 scripts, mock-dashboard components, and Next.js files out of the runtime and runbook. Do not spend hackathon time deleting them unless they interfere with builds.
4. Update `docs/demo/RUNBOOK.md` so it documents only the canonical Docker Compose flow.

Acceptance criteria:

- One documented command starts the platform.
- One documented command starts the scenario.
- No presentation step depends on an old demo script or mock-data page.

### Phase 2 — Make scenario evidence deterministic

1. Generate the surge evidence inside one predictable 30-minute event-time window.
2. Ensure that window contains enough events to meet the existing detector contracts:
   - order-volume minimum and threshold;
   - preparation sample minimum and threshold;
   - cancellation order/sample minimum and threshold;
   - supporting handoff/review minimums when enabled.
3. Keep recovery events in a later, clearly separated verification window.
4. Use the seed for all random values and make event IDs deterministic.
5. Add a scenario contract test that builds snapshots from generated events and proves the required signals correlate into `OPERATIONAL_OVERLOAD`.

Primary files:

- `simulator/lossline_simulator/scenarios/lunch_rush.py`
- `simulator/lossline_simulator/runner.py`
- `simulator/tests/test_simulator.py`

Acceptance criteria:

- The same seed creates identical events.
- Degradation events create all required signals in one correlatable window.
- Recovery events do not create a second overload incident.

### Phase 3 — Remove the contradictory M0 incident path

1. Remove or disable the cancellation-only incident fallback in `run_detection_pipeline()`.
2. Continue persisting standalone signals for evidence, but create an incident only when the full overload correlation rule succeeds.
3. Keep incident deduplication so repeated events update the existing open incident rather than create another one.
4. Add tests proving:
   - cancellation alone creates a signal but no incident;
   - required correlated signals create one incident;
   - replaying the trigger does not create a duplicate incident.

Primary files:

- `apps/backend/src/intelligence/pipeline.py`
- `apps/backend/src/intelligence/persistence.py`
- `apps/backend/tests/test_intelligence_pipeline.py`
- `apps/backend/tests/test_m1_end_to_end.py`

Acceptance criteria:

- No incident can be `AWAITING_APPROVAL` without a recommendation.
- The canonical scenario produces exactly one incident.

### Phase 4 — Make the AI and LangGraph boundary truthful

1. Keep all metrics, correlation, confidence, revenue, recommendation, and outcome calculations outside the LLM.
2. Keep LangGraph as post-detection orchestration for context loading, confidence routing, explanation, recommendation handoff, and finalization.
3. Make the bounded `widen_context` node do one real, small operation or rename it to reflect that it only records a retry. Do not present a no-op as a fresh investigation.
4. Persist and return these explanation fields clearly:
   - explanation text;
   - `explanation_source` (`LLM` or `TEMPLATE`);
   - provider model;
   - fallback reason when applicable.
5. Do not implement durable LangGraph approval interrupt/resume during this fix unless the existing approval flow cannot meet the demo output. Describe approval as an API-managed human gate.

Primary files:

- `apps/backend/src/intelligence/langgraph_workflow.py`
- `apps/backend/src/intelligence/explanations.py`
- `apps/backend/src/intelligence/persistence.py`
- `apps/backend/tests/test_workflow_outcome.py`

Acceptance criteria:

- The demo works without an LLM key using `TEMPLATE`.
- A configured provider can produce `LLM`, and invalid/failed output falls back safely.
- No AI-generated value is used as a business calculation.

### Phase 5 — Correct approval and outcome lifecycle

1. Allow approval only for `AWAITING_APPROVAL` incidents with a valid, non-expired recommendation.
2. Treat approval as simulated action execution and label it accordingly.
3. Treat rejection as a valid `ACTION_REJECTED` decision, not an execution failure.
4. Preserve decision idempotency.
5. Allow verification only after approval and sufficient recovery events.
6. Ensure outcome mapping is consistent:
   - `IMPROVED` → incident `RESOLVED`;
   - insufficient recovery data → remain verifiable or return `INSUFFICIENT_DATA` without claiming success;
   - no improvement → incident `NOT_IMPROVED`.
7. Add transition tests for approve, reject, duplicate decision, expired recommendation, insufficient recovery, and improved recovery.

Primary files:

- `apps/backend/src/api/endpoints.py`
- `apps/backend/src/intelligence/outcomes.py`
- `apps/backend/tests/test_workflow_outcome.py`

Acceptance criteria:

- Invalid lifecycle transitions return `409`.
- Approval followed by canonical recovery ends in `RESOLVED` with `IMPROVED`.

### Phase 6 — Align the frontend with backend truth

1. Add every backend status used by the demo to the TypeScript contract, including `MONITOR_ONLY` if retained.
2. Define one shared frontend rule for terminal versus active incidents.
3. Display `NOT_IMPROVED`, `MONITOR_ONLY`, and `ACTION_REJECTED` correctly.
4. Show that revenue exposure and all scenario data are synthetic estimates.
5. Show explanation source as `AI-generated` only when the source is `LLM`; otherwise use `Deterministic summary`.
6. Hide approval controls unless an incident is `AWAITING_APPROVAL` and has a recommendation.
7. Keep REST authoritative and use WebSocket notifications only to trigger refreshes.

Primary files:

- `apps/frontend/src/types/api.ts`
- `apps/frontend/src/pages/OverviewPage.tsx`
- `apps/frontend/src/pages/IncidentDetailPage.tsx`
- `apps/frontend/src/pages/ActionsPage.tsx`
- `apps/frontend/src/components/common/StatusChip.tsx`

Acceptance criteria:

- Frontend TypeScript build passes.
- No terminal incident appears in the active count.
- The UI never presents template prose as LLM output.
- Approval cannot be attempted for an incident without a recommendation.

### Phase 7 — Add minimum Redis safety for the demo

1. Preserve the current rule: commit derived PostgreSQL state before acknowledging a stream message.
2. Add a small pending-message reclaim pass using `XAUTOCLAIM` so a crashed delivery can be retried.
3. Reuse the existing retry limit and DLQ.
4. Confirm that replay is idempotent and cannot create duplicate incidents.
5. Do not redesign the outbox table during the hackathon. Document that the single-backend topology is required for the demo.

Primary files:

- `apps/backend/src/streaming/consumer.py`
- `apps/backend/src/streaming/outbox_worker.py`
- `apps/backend/tests/test_outbox_streaming.py`

Acceptance criteria:

- Successful runs leave `XPENDING` at zero.
- Poison messages reach `restaurant.events.dlq` only after the configured attempt limit.
- Reclaimed or duplicate events do not create duplicate incidents.

### Phase 8 — Create one automated demo smoke check

Add a small integration script or pytest that uses the real FastAPI ingestion contract and performs:

1. reset synthetic data;
2. submit canonical degradation events;
3. assert exactly one overload incident and one recommendation;
4. approve using an idempotency key;
5. submit recovery events;
6. verify the outcome;
7. assert `IMPROVED` and `RESOLVED`.

Use SQLite with inline processing for the fast automated check. Keep the Docker run as the final Redis/PostgreSQL verification.

Primary files:

- `apps/backend/tests/test_m1_end_to_end.py`
- `docs/demo/RUNBOOK.md`

Acceptance criteria:

- The automated smoke check is deterministic.
- The Docker demo produces the same domain result.

## 5. Verification Gates

Run each suite separately because the repository currently has conflicting top-level `tests` packages.

### Gate A — Intelligence

```bash
.venv/bin/pytest packages/intelligence/tests/ -q
```

### Gate B — Backend

```bash
PYTHONPATH=apps/backend:packages/intelligence/src \
.venv/bin/pytest apps/backend/tests/ -q
```

### Gate C — Simulator

```bash
PYTHONPATH=apps/backend:simulator \
.venv/bin/pytest simulator/tests/ -q
```

### Gate D — Frontend

```bash
cd apps/frontend
npm ci
npm run build
```

### Gate E — Docker integration

```bash
docker compose down
docker compose up --build -d postgres redis backend frontend
curl -fsS http://localhost:8000/ready
docker compose --profile demo run --rm simulator
```

After approval and recovery, verify:

```bash
curl -s http://localhost:8000/api/v1/incidents | jq
curl -s http://localhost:8000/api/v1/analytics/summary | jq
docker compose exec redis redis-cli XPENDING restaurant.events detection
docker compose exec redis redis-cli XLEN restaurant.events.dlq
docker compose logs backend | rg -i "error|exception|traceback|failed"
```

## 6. Final Definition of Done

The fix is complete when:

- all intelligence, backend, and simulator tests pass;
- the frontend production build passes;
- Docker readiness passes;
- one seeded scenario produces exactly one `OPERATIONAL_OVERLOAD` incident;
- the incident has required evidence, confidence, estimated exposure, explanation, and recommendation;
- approval is idempotent and recovery produces `IMPROVED`;
- the incident ends as `RESOLVED`;
- Redis has no pending or dead-letter messages after a successful run;
- backend logs contain no unexplained errors;
- the complete demo succeeds three consecutive times from reset;
- the presentation accurately describes deterministic intelligence, LangGraph orchestration, the human approval gate, and optional LLM explanation.

## 7. Recommended Execution Order

Work in this order and do not start later phases while an earlier acceptance criterion is failing:

1. Canonical scenario and window alignment.
2. Remove the M0 incident fallback and prove one-incident deduplication.
3. Correct approval/outcome lifecycle.
4. Align frontend states and AI labels.
5. Add Redis pending-message reclaim.
6. Complete the automated smoke check and run the Docker demo three times.

This order prioritizes the visible end-to-end result while preserving the deterministic intelligence foundation already present.
