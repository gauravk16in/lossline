# Project Coding Rules (Non-Obvious Only)

- **Pydantic `BaseModel` vs `@dataclass`**: Use Pydantic only for validated I/O contracts (`Signal`, `MetricSnapshot`). Use `@dataclass(frozen=True)` for internal domain objects (`IncidentCandidate`, `ConfidenceResult`, etc.) — mixing them is a type boundary mistake.
- **New source modules go under `packages/intelligence/src/lossline_intelligence/`** — the stray `packages/intelligence/lossline_intelligence/` tree is dead; the editable install resolves to `src/`.
- **Run tests from the repo root**: `.venv/bin/pytest packages/intelligence/tests/` — root `.venv` is the shared environment.
- **All Pydantic models require `ConfigDict(extra="forbid", frozen=True)`** — omitting silently accepts extra fields and makes the model mutable.
- **`Decimal` (not `float`) for all metric fields**; use `quantize(Decimal("0.0001"), ROUND_HALF_UP)` and validate finite via `require_finite_decimal`.
- **Use `build_signal_id()` from `detectors/_common.py`** for signal IDs — don't reimplement the `sig_{prefix}_{outlet_id}_{window_tag}_{version}` pattern manually.
- **Call `require_matching_outlet()` from `detectors/_common.py`** at the top of every detector — it raises `ValueError` on outlet mismatch (programming error, not data quality).
- **`outlet_id` is canonical** — never use `restaurant_id` for new code; it is only a backward-compat `@property` alias on `IncidentCandidate`.
- **All CONFIG_DEFAULT constants are keyword arguments** to detector/scorer functions — pass overrides rather than monkey-patching module globals.
- **Use `recommend()` (not `recommend_action()`)** for new code — `recommend_action()` swallows abstentions; `recommend()` returns the typed `RecommendationAbstention` for proper handling.
- **Shared test fixtures live in `tests/fixtures/`** — use factory functions returning `dict` with `| {...}` merges, not pytest fixtures.
- **`StrEnum` for all enumerations** — not `str + Literal`, not plain `Enum`.
- **Timestamps must be timezone-aware**; validators call `.astimezone(timezone.utc)`. Naive datetimes raise `ValueError`.
- **ID collections are `tuple[..., ...]`** (immutable), not `list` — frozen dataclasses and frozen Pydantic models both require this.
