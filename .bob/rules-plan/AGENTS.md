# Project Architecture Rules (Non-Obvious Only)

- **Pydantic models are I/O contract boundaries only** — `Signal` and `MetricSnapshot` are validated at serialization edges. Internal pipeline objects (`IncidentCandidate`, `ConfidenceResult`, `Recommendation`) are `@dataclass(frozen=True)` — this is a deliberate architectural boundary, not an oversight.
- **`CANCELLATION_SPIKE` is a required correlation signal** (see `correlation/rules.py`) — the plan says "at least one of handoff/cancellation" but the code requires both volume+prep+cancellation. `HANDOFF_DELAY_SPIKE` and `DELAY_REVIEW_SPIKE` are supporting-only.
- **`correlate_signals()` returns one candidate per call** — it stops at the first qualifying outlet and returns. Multi-outlet handling requires calling it per outlet.
- **`outlet_id` is the operational identity** throughout the intelligence pipeline — `restaurant_id` on `IncidentCandidate` is a backward-compat property alias only; correlation, deduplication, and isolation all use `outlet_id`.
- **Intelligence package location must be resolved before broader implementation** — `docs/architecture.md` explicitly says "`packages/intelligence/` or `services/intelligence/`" — the backend will import whichever wins; do not design the import path until this is decided.
- **Deterministic code owns all numeric outputs** — LLM (`ExplanationProvider`) may produce prose only. It never calculates metrics, confidence, revenue, recommendation selection, or outcome status.
- **LangGraph fires only after deterministic correlation creates an incident** — never per raw event.
- **Redis `restaurant.events` is the only stream** — one consumer group (`detection`) in M1.
- **Transactional outbox is mandatory** — event + outbox in one PostgreSQL transaction; Redis unavailability leaves outbox pending, not silent data loss.
- **Incident deduplication fingerprint**: `(outlet_id, incident_type, correlation_rule_version)` — resolved/rejected incidents are never reopened.
- **All actions require manager approval** — high confidence does not bypass this in M1.
- **WebSocket is non-durable** — REST is authoritative; reconnect reloads state via REST, not WebSocket history.
- **Demo reset is only available in demo mode** and may only delete records tied to validated synthetic scenario runs — returns `404` otherwise.
- **All UI restaurant data must show "Synthetic data for demonstration."** — frozen requirement.
