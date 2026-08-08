# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Status

LOSSLine is in early implementation. `FINAL_IMPLEMENTATION_PLAN.md` is the implementation authority; `IMPLEMENTATION_PLAN.md` is superseded. Most directories (`apps/`, `services/`, `simulator/`, `docs/`, `scripts/`) contain only empty placeholder files. The only implemented package is `packages/intelligence/`.

The `app/` directory (with placeholder `x.txt`/`y.txt`) is distinct from `apps/` — both exist but only `apps/` is the intended target from the plan. Do not add code to `app/`.

## Python Environment

The root `.venv/` is the shared virtual environment for all Python packages. Use `.venv/bin/python` and `.venv/bin/pytest` — do not create per-package venvs. Python 3.12 is required (`requires-python = ">=3.12"`).

`lossline-intelligence` is installed into `.venv` as an editable package (`pip install -e packages/intelligence`). The authoritative source is `packages/intelligence/src/lossline_intelligence/`. There is also a stray `packages/intelligence/lossline_intelligence/` tree that predates the `src/` layout — the installed package resolves to `src/`, so new modules go under `src/lossline_intelligence/`.

## Build, Test, and Lint Commands

No `Makefile` exists yet. Commands to run from the **repo root**:

```bash
# Run all intelligence tests
.venv/bin/pytest packages/intelligence/tests/

# Run a single test
.venv/bin/pytest packages/intelligence/tests/test_signal_model.py::test_signal_accepts_valid_detector_output -v

# Install intelligence package in editable mode (first-time setup)
.venv/bin/pip install -e "packages/intelligence[dev]"
```

`pytest` picks up config from `packages/intelligence/pyproject.toml` (`testpaths = ["tests"]`) when invoked from `packages/intelligence/`, but running from the repo root with an explicit path also works.

No formatter, linter, or type-checker config has been committed yet. When adding them, use `ruff` for formatting/linting and `mypy` or `pyright` for types, and add config to `packages/intelligence/pyproject.toml`.

## Package Build System

`packages/intelligence` uses `hatchling==1.27.0` as its build backend (pinned). Dependency versions are also pinned (`pydantic==2.11.7`, `pytest==8.4.1`). Continue pinning all dependencies.

## Code Style (from existing source)

- **Pydantic models** use `model_config = ConfigDict(extra="forbid", frozen=True)` — all domain models are immutable and reject unknown fields.
- **Decimal** (not `float`) for all metric values; validated as finite via `field_validator`.
- **Timestamps** are always timezone-aware and normalized to UTC in validators (`value.astimezone(timezone.utc)`). Naive datetimes are rejected.
- **`evidence_event_ids`** and similar ID collections use `tuple[Identifier, ...]` (immutable), not `list`.
- **`Identifier`** is a module-level type alias: `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]` — reuse it, do not inline bare `str` for IDs.
- **`StrEnum`** is used for signal/event type enumerations, not `str` + `Literal`.
- Tests use a `signal_data()` factory function (not a pytest fixture) for baseline valid data, then apply `| {...}` dict merges for variations.

## Architecture Constraints (frozen)

- **LLM never calculates metrics, confidence, revenue, recommendations, or outcomes** — deterministic code owns all numeric outputs; LLM produces only grounded prose explanation.
- **Simulator must call `POST /events`** — never bypass the ingestion API to write directly to DB or Redis.
- **`restaurant.events` is the only Redis stream in M1** — no other streams.
- **All numeric thresholds and weights are `CONFIG_DEFAULT`**, not business facts — put them in versioned config, never hardcode in business logic.
- **Demo currency is INR** (`₹`) for the M1 lunch-rush scenario; revenue estimates must label assumptions and use "Estimated revenue exposure," never "profit loss."
- **All UI restaurant data must show "Synthetic data for demonstration."**

## Testing Conventions

- Test files named `test_<module>.py` live in `packages/<pkg>/tests/` (not alongside source).
- Every deterministic rule needs: below-threshold, at-threshold, above-threshold, sparse-data, and repeatability fixtures.
- Fake all LLM calls in automated tests.
- Integration tests must prove Redis crash recovery and PostgreSQL outbox idempotency.
