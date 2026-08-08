# Project Architecture Rules (Non-Obvious Only)

- **Deterministic code owns all numeric outputs** — LLM (`ExplanationProvider`) produces only prose from structured inputs; it must never select recommendations, alter state, or introduce numbers not present in evidence.
- **LangGraph starts only after deterministic correlation creates an incident** — it never fires per event; it is the investigation/approval/resume orchestrator, not the detector.
- **Redis `restaurant.events` is the only stream** — the plan explicitly names one consumer group (`detection`) and one stream for M1.
- **Transactional outbox pattern is mandatory** — event insert + outbox row in one transaction; publisher marks complete after Redis append. Redis unavailability must leave accepted events in the outbox for recovery, not silently drop them.
- **Incident deduplication is by fingerprint** `(restaurant_id, incident_type, correlation_rule_version)` — resolved/rejected incidents are never reopened by late events; only active-status incidents merge new signals.
- **All actions are medium-risk and require approval** — high confidence does not bypass the manager approval step in M1.
- **WebSocket is non-durable presentation only** — REST is authoritative; reconnect must reload state from REST, not replay WebSocket history.
- **Confidence `<.50` triggers exactly one LangGraph retry** (evidence window widened by ±1 hour) before becoming `MONITOR_ONLY` with no recommendation — the retry count ceiling is config, not code logic.
- **Revenue display must use "Estimated revenue exposure"** and show horizon/inputs; never claim profit loss or causal certainty.
- **Demo reset endpoint must check demo mode and synthetic scenario IDs** before deleting anything — returning `404` in non-demo mode is a safety requirement, not a convenience.
- **`app/` directory is a dead placeholder** — the plan targets `apps/backend/` and `apps/frontend/`; new backend/frontend code belongs in `apps/`.
- **All restaurant UI data must display "Synthetic data for demonstration."** — this is a frozen requirement, not a style choice.
