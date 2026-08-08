# Project Coding Rules (Non-Obvious Only)

- **Add new source modules under `packages/intelligence/src/lossline_intelligence/`**, not under the stray `packages/intelligence/lossline_intelligence/` tree — the editable install resolves to `src/`.
- **Run tests from the repo root** using `.venv/bin/pytest packages/intelligence/tests/` — the root `.venv` is the shared environment; do not create per-package venvs.
- **All Pydantic domain models must set `ConfigDict(extra="forbid", frozen=True)`** — without this the model silently accepts extra fields and becomes mutable.
- **Use `Decimal` (not `float`) for all metric fields** and validate with `require_finite_decimal` — existing validators must be replicated in every new model.
- **Reuse the `Identifier` type alias** from the module rather than inlining `str` — it enforces non-empty, stripped strings and is the contract boundary.
- **All numeric thresholds and weights belong in versioned config, never in business logic** — hardcoding one makes it a claimed fact, not a calibratable default.
- **Tests use plain factory functions** (e.g., `signal_data() -> dict`) with `| {...}` dict merges for variations, not pytest fixtures — follow this pattern for consistency.
- **`StrEnum` for enumerations**, not `str` + `Literal` or plain `Enum`.
- **Timestamps must be timezone-aware** and validators must call `.astimezone(timezone.utc)`; naive datetimes raise `ValueError` by convention.
- **`evidence_event_ids` and source ID collections are `tuple[..., ...]`**, not `list` — frozen models require immutable containers.
