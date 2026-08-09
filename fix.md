  ## What you should fix first

  ### P0 — Must fix before the demo

  #### 1. Stabilize one canonical scenario

  Use only the main lunch-rush simulator:

  simulator/lossline_simulator/scenarios/lunch_rush.py

  The scenario must consistently produce:

  Normal operation
  → overload detected
  → exactly one OPERATIONAL_OVERLOAD incident
  → recommendation displayed
  → manager approves
  → recovery events arrive
  → outcome becomes IMPROVED
  → incident becomes RESOLVED

  Run it at least three times from a clean state. If it behaves differently between runs, the demo is not ready.

  #### 2. Stop the broken M0 cancellation incident

  The pipeline currently creates a cancellation-only incident that can be:

  - AWAITING_APPROVAL;
  - missing a recommendation;
  - impossible to approve through the API.

  For the hackathon, the cleanest solution is to disable the M0 fallback and show only correlated OPERATIONAL_OVERLOAD incidents.

  The relevant section is in:

  apps/backend/src/intelligence/pipeline.py

  #### 3. Align the scenario with detector windows

  All required evidence must overlap in the same correlation window:

  - ORDER_VOLUME_SPIKE
  - PREP_TIME_SPIKE
  - CANCELLATION_SPIKE

  Keep supporting evidence in the same window:

  - HANDOFF_DELAY_SPIKE
  - DELAY_REVIEW_SPIKE

  Right now, the simulator spreads evidence across phases and multiple sliding windows. That can produce late or inconsistent incidents.

  For the demo, emit the main surge, delayed-preparation events, and cancellations inside one predictable 30-minute event-time window.

  #### 4. Ensure exactly one incident is generated

  After the degradation events:

  curl -s http://localhost:8000/api/v1/incidents | jq

  Verify:

  - exactly one active incident;
  - incident_type is OPERATIONAL_OVERLOAD;
  - status is AWAITING_APPROVAL;
  - confidence exists;
  - at least three signals are linked;
  - a recommendation exists;
  - explanation exists;
  - revenue exposure is clearly labeled as estimated/synthetic.

  #### 5. Decide what you are claiming about AI

  For the presentation, be precise:

  - Detectors and calculations are deterministic.
  - LangGraph orchestrates the investigation stages.
  - The LLM only writes a grounded manager explanation.
  - Manager approval controls the action.
  - Outcome verification is deterministic.

  If you want to claim that a real LLM is running, configure LLM_API_KEY and visibly expose:

  explanation_source = LLM

  Otherwise say:

  > The demo uses the deterministic explanation fallback, so it works without an external AI provider.

  Do not claim that LangGraph currently performs durable approval pause/resume. It does not.

  #### 6. Fix status mismatches in the UI

  The backend can return MONITOR_ONLY, but the frontend type does not include it.

  Also ensure terminal statuses are handled consistently:

  - RESOLVED
  - ACTION_REJECTED
  - NOT_IMPROVED
  - potentially MONITOR_ONLY

  Otherwise resolved or monitor-only incidents may continue appearing as active.

  #### 7. Remove demo confusion

  Before presenting, choose one UI and one demo route.

  The active application is the Vite React app. Ignore or remove from the presentation path:

  - old Next.js app/ files;
  - unused mock dashboard components;
  - unused mock data;
  - old demo_m0_pipeline.py;
  - alternative M1 scripts unless used strictly for testing.

  You do not necessarily need to delete them immediately, but nobody should accidentally launch the wrong app or scenario.

  ———

  ## P1 — Important after the demo works

  ### 8. Make approval semantics honest

  Currently approval immediately becomes EXECUTED, even though no real POS/KDS action is executed.

  For now use wording such as:

  Action acknowledged

  or:

  Simulated action executed

  A rejection should not have execution status FAILED. It should be something like:

  NOT_EXECUTED

  ### 9. Scope demo reset safely

  POST /demo/reset currently removes practically all operational data.

  For the hackathon, ensure:

  - DEMO_MODE=true;
  - the endpoint cannot run in production;
  - all displayed data is synthetic.

  Afterward, scope deletion by scenario_id or run_id.

  ### 10. Fix Redis retry behavior

  The code has retry counters and a DLQ, but pending messages are not properly reclaimed or redelivered.

  After the demo:

  - use XAUTOCLAIM;
  - track delivery attempts;
  - retry pending messages;
  - move poison messages to the DLQ;
  - acknowledge only after derived database writes commit.

  ### 11. Connect ScenarioRun properly

  Every synthetic event should carry a persisted run_id, and every incident/WebSocket update should be traceable to that run.

  This prevents one demo run from mixing with another.

  ### 12. Remove fixture-baseline deception

  Fixture baselines are fine for a controlled demo, but label them clearly.

  Either:

  - use real simulator history only; or
  - show baseline_source: DEMO_FIXTURE.

  Do not imply that a fixture-generated baseline was learned from historical POS data.

  ———`