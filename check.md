
  # Proper way to check everything

  ## 1. Check repository state

  Before testing:

  cd /Users/kr/Desktop/Lossline
  git status --short
  git log --oneline -5

  This confirms what is modified and which commit you are demonstrating.

  ## 2. Run intelligence tests

  .venv/bin/pytest packages/intelligence/tests/ -q

  Current expected result:

  191 passed

  These cover the deterministic intelligence logic.

  ## 3. Run backend tests

  PYTHONPATH=apps/backend:packages/intelligence/src \
  .venv/bin/pytest apps/backend/tests/ -q

  Current expected result:

  18 passed

  ## 4. Run simulator tests

  PYTHONPATH=apps/backend:simulator \
  .venv/bin/pytest simulator/tests/ -q

  Current expected result:

  1 passed

  Do not combine all three directories in one pytest command. The repository currently has conflicting top-level tests packages, which causes
  collection errors.

  ## 5. Check the frontend

  cd apps/frontend
  npm ci
  npm run build

  Expected result:

  ✓ built

  Warnings currently expected:

  - Vite module/config warning;
  - large JavaScript bundle warning.

  Then return to the root:

  cd ../..

  ## 6. Start the complete system

  Start fresh:

  docker compose down
  docker compose up --build -d postgres redis backend frontend

  Watch container status:

  docker compose ps

  All four services should be running, and PostgreSQL/backend/Redis should be healthy.

  ## 7. Check backend readiness

  curl -s http://localhost:8000/health | jq
  curl -s http://localhost:8000/ready | jq

  Expected:

  {"status":"healthy"}

  and:

  {"status":"ready"}

  /ready is the more meaningful check because it verifies infrastructure access.

  ## 8. Check the empty state

  Reset demo data:

  curl -s -X POST http://localhost:8000/api/v1/demo/reset | jq

  Then verify:

  curl -s http://localhost:8000/api/v1/incidents | jq
  curl -s http://localhost:8000/api/v1/analytics/summary | jq

  Expected:

  - incidents: []
  - incident count: 0
  - active incident count: 0

  ## 9. Open the frontend

  Open:

  http://localhost:3000

  Before running the simulator, check:

  - page loads;
  - connection badge becomes live;
  - zero incidents are displayed;
  - no fake mock outlets appear;
  - browser console contains no API or React errors.

  ## 10. Run the real simulator

  In a second terminal:

  docker compose --profile demo run --rm simulator

  Watch backend and worker activity:

  docker compose logs -f backend

  Expected log progression:

  events accepted
  → outbox events published
  → Redis messages consumed
  → signals detected
  → overload incident persisted
  → awaiting approval

  ## 11. Inspect the incident through REST

  While the simulator is waiting for approval:

  curl -s http://localhost:8000/api/v1/incidents | jq

  Copy the incident ID and inspect it:

  curl -s http://localhost:8000/api/v1/incidents/INCIDENT_ID | jq

  Replace INCIDENT_ID with the actual integer.

  Check:

  - incident_type == "OPERATIONAL_OVERLOAD"
  - status == "AWAITING_APPROVAL"
  - signals contains the expected required signals
  - recommendations is non-empty
  - confidence is between 0 and 1
  - revenue is estimated and plausible
  - explanation only mentions supplied evidence

  ## 12. Approve through the UI

  Open the incident and approve the recommendation.

  Immediately check:

  curl -s http://localhost:8000/api/v1/incidents/INCIDENT_ID | jq

  Expected intermediate status:

  ACTION_APPROVED

  The simulator should then resume and post recovery events.

  ## 13. Verify final outcome

  After the simulator completes:

  curl -s http://localhost:8000/api/v1/incidents/INCIDENT_ID | jq
  curl -s http://localhost:8000/api/v1/incidents/INCIDENT_ID/outcome | jq
  curl -s http://localhost:8000/api/v1/analytics/summary | jq

  Target result:

  Incident status: RESOLVED
  Outcome status: IMPROVED
  Resolved incident count: 1

  Also check the frontend updates without a manual reload.

  ## 14. Inspect Redis

  Check stream size and consumer state:

  docker compose exec redis redis-cli XLEN restaurant.events
  docker compose exec redis redis-cli XINFO GROUPS restaurant.events
  docker compose exec redis redis-cli XPENDING restaurant.events detection
  docker compose exec redis redis-cli XLEN restaurant.events.dlq

  For a successful demo:

  - main stream contains events;
  - consumer group exists;
  - pending count should ideally be 0;
  - DLQ should be empty or nonexistent.

  ## 15. Inspect logs for hidden failures

  docker compose logs backend | rg -i "error|exception|traceback|failed"

  Any unexplained output here should be treated as a demo blocker.

  ## 16. Repeatability check

  Run this complete sequence three times:

  reset
  → simulator
  → approve
  → recovery
  → verify

  Each run should produce:

  - one overload incident;
  - one recommendation;
  - one approval;
  - one improved outcome;
  - zero pending Redis messages;
  - zero DLQ messages;
  - no backend traceback.

  That repeatability check is more important for your hackathon than adding another “AI agent.”

  ## Minimum demo-ready definition

  You are ready only when all of these are true:

  - 191 intelligence tests pass.
  - 18 backend tests pass.
  - Simulator test passes.
  - Frontend builds.
  - Docker services become healthy.
  - Simulator produces exactly one overload incident.
  - Incident contains correlated evidence.
  - Recommendation exists and can be approved.
  - Recovery produces IMPROVED.
  - Incident finishes as RESOLVED.
  - Redis has no pending or dead-letter messages.
  - The same result occurs three consecutive times.
  - You accurately describe the LLM and LangGraph limitations.

  That should be the team’s immediate definition of done.