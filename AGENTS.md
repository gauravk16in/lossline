# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Status

LOSSLine is in active implementation. `FINAL_IMPLEMENTATION_PLAN.md` is the implementation authority; `IMPLEMENTATION_PLAN.md` is superseded. `docs/architecture.md` is the architectural summary.

The canonical application layout is `apps/backend/`, `apps/frontend/`, `packages/intelligence/`, and `simulator/`. Backend intelligence orchestration lives under `apps/backend/src/intelligence/`; deterministic domain logic lives only under `packages/intelligence/`.

Do not recreate the obsolete singular `app/` tree or add a second intelligence implementation under `services/intelligence/`.

## Python Environment

The root `.venv/` is the shared virtual environment. Python 3.12 required. `lossline-intelligence` is already installed in editable mode — no setup needed before running tests.

The stray `packages/intelligence/lossline_intelligence/` tree (no-`src/` layout) has been cleaned up. All source lives under `packages/intelligence/src/lossline_intelligence/`. New modules go there.

## Commands (from repo root)

```bash
# Run all tests
.venv/bin/pytest packages/intelligence/tests/

# Run a single test
.venv/bin/pytest packages/intelligence/tests/test_signal_model.py::test_signal_accepts_valid_detector_output -v

# First-time setup
.venv/bin/pip install -e "packages/intelligence[dev]"
```

No Makefile, formatter, linter, or type-checker config has been committed yet. When adding: use `ruff` + `mypy`/`pyright`, configured in `packages/intelligence/pyproject.toml`. Pin all dependency versions.

## Code Style (from source)

**Two model patterns — use the right one:**
- **Pydantic `BaseModel`** (`ConfigDict(extra="forbid", frozen=True)`) for validated I/O contracts: `Signal`, `MetricSnapshot`. These are serialization boundaries.
- **`@dataclass(frozen=True)`** for internal pure domain objects: `IncidentCandidate`, `QualityFlags`, `ConfidenceResult`, `Recommendation`. No Pydantic validation overhead for internal types.

**`Identifier` type alias** — `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` — defined per module, not shared via import. Reuse, never inline bare `str` for IDs.

**`Decimal` (not `float`) for all metric values**; validate as finite with `require_finite_decimal`. Use `quantize(_DP, rounding=ROUND_HALF_UP)` with `_DP = Decimal("0.0001")`.

**`StrEnum`** for all enumerations (`SignalType`, `Severity`, `IncidentType`, `ConfidenceTier`, etc.).

**Timestamps** — always timezone-aware; Pydantic validators call `.astimezone(timezone.utc)`. Naive datetimes are rejected.

**ID collections** — `tuple[Identifier, ...]` (immutable), not `list`. Validated unique.

**Detector signal IDs are deterministic** — format `sig_{prefix}_{outlet_id}_{window_start_utc}_{DETECTOR_VERSION}`. Use `build_signal_id()` from [`detectors/_common.py`](packages/intelligence/src/lossline_intelligence/detectors/_common.py) — do not reimplement.

**`outlet_id` is the canonical field** on all domain models. `restaurant_id` exists only as a `@property` alias on `IncidentCandidate` for downstream compatibility — never use it for new code.

## Package Structure

```
src/lossline_intelligence/
  models/          # Signal, SignalType, Severity, SEVERITY_SCORE, IncidentCandidate
  aggregation/     # MetricSnapshot, MetricSnapshotBuilder, BaselineResult
  detectors/       # _common.py shared utilities + 5 detector modules
  correlation/     # engine.py (correlate_signals), rules.py (REQUIRED/SUPPORTING types)
  scoring/         # confidence.py, revenue_risk.py
  recommendations/ # playbooks.py (Playbook dataclasses), engine.py (recommend())
  pipelines/       # confidence.py, correlation.py, outcome.py, recommendations.py, revenue.py
  agents/          # (legacy agent wrappers — prefer detectors/ for new work)
```

## Critical Non-Obvious Rules

- **`CANCELLATION_SPIKE` is a REQUIRED signal** (not optional) in `correlation/rules.py` — the implementation differs from the plan's "at least one of handoff/cancellation" wording. `HANDOFF_DELAY_SPIKE` and `DELAY_REVIEW_SPIKE` are supporting.
- **`correlate_signals()` returns one candidate per call** — it stops at the first qualifying outlet. M1 only.
- **`recommend()` returns `Recommendation | RecommendationAbstention`** — `recommend_action()` is a backward-compat alias returning `None` on abstention. Use `recommend()` for new code.
- **All CONFIG_DEFAULT thresholds/weights are module-level constants**, never hardcoded in logic — callers pass overrides as keyword arguments.
- **Detectors share utilities via `detectors/_common.py`** — `require_matching_outlet`, `window_tag`, `build_signal_id`, `robust_z_score`, `deviation_ratio`. New detectors must use these.
- **LLM never calculates metrics, confidence, revenue, recommendations, or outcomes.** Deterministic code owns all numbers; LLM produces only grounded prose.
- **Simulator must call `POST /events`** — never write directly to DB or Redis.

## Testing Conventions

Tests live in `packages/intelligence/tests/`. Shared fixture factories in `tests/fixtures/`. Use plain factory functions (e.g., `signal_data() -> dict`) with `| {...}` dict merges — not pytest fixtures. Every deterministic rule needs: below-threshold, at-threshold, above-threshold, sparse-data, and repeatability cases. Fake all LLM calls.
