# Project Documentation Context (Non-Obvious Only)

- **`FINAL_IMPLEMENTATION_PLAN.md` is the implementation authority** — `IMPLEMENTATION_PLAN.md` is superseded. `docs/architecture.md` is the architectural summary; it explicitly defers to the plan for contracts and config.
- **Intelligence code location is unresolved**: `docs/architecture.md` says "`packages/intelligence/` or `services/intelligence/`" — both exist but only `packages/intelligence/` has real code. Do not assume `services/intelligence/` is the target.
- **Only `packages/intelligence/` contains real code** — `apps/backend/`, `apps/frontend/`, `services/intelligence/`, `simulator/`, `docs/` (except `architecture.md`), `scripts/` are empty stubs.
- **`app/` (with `x.txt`/`y.txt`) ≠ `apps/`** — `apps/` is the plan target; `app/` is a dead placeholder.
- **`claude.md` at root is just `@AGENTS.md`** — not a separate rules file.
- **`CANCELLATION_SPIKE` is a required signal** in the correlation engine — the implementation differs from the plan's "at least one of handoff/cancellation" wording; the code in `correlation/rules.py` is authoritative.
- **`restaurant_id` does not appear as a field** on any domain model in `src/` — `outlet_id` is canonical everywhere; `restaurant_id` is only a `@property` alias on `IncidentCandidate` for backward compatibility.
- **All numeric values labeled `CONFIG_DEFAULT`** in the plan are module-level constants in source, passed as overrideable keyword arguments — never treat them as business facts.
- **198 tests pass** as of last commit — run `.venv/bin/pytest packages/intelligence/tests/ -q` to verify before answering questions about correctness.
