# Repository Guidelines

## Project Structure & Module Organization

LOSSLine is currently in its planning stage. The intended repository boundaries are:

- `apps/backend/`: FastAPI application, persistence models, and HTTP endpoints.
- `apps/frontend/`: operator dashboard and incident/action workflows.
- `services/intelligence/`: deterministic aggregation, anomaly detection, correlation, confidence scoring, and recommendations.
- `simulator/`: synthetic restaurant events and repeatable demo scenarios.
- `docs/`: architecture and implementation decisions. Start with `docs/Restaurant Implementation Plan.md` before changing system boundaries.

Keep the MVP a modular monolith. Share explicit event, signal, and incident contracts instead of coupling modules through internal implementation details.

## Build, Test, and Development Commands

No package manifests, build scripts, or test runners are committed yet. When bootstrapping a component, document its setup in the root README and expose predictable commands such as `make dev`, `make test`, and `make lint`. Pin dependencies and commit lockfiles.

## Coding Style & Naming Conventions

For Python, use 4-space indentation, type annotations, `snake_case` for functions/modules, and `PascalCase` for classes and Pydantic models. Keep detectors deterministic and side-effect free where practical; confidence calculations must remain explainable and capped at `0.95`. Prefer small modules organized by domain over generic utility collections.

For frontend code, use `PascalCase` for components and `camelCase` for variables and hooks. Add formatter and linter configuration with the first implementation.

## Testing Guidelines

Place tests near their owning package or in a package-level `tests/` directory, using names such as `test_cancellation_detector.py`. Prioritize unit tests for baselines, detectors, confidence boundaries, and recommendation rules. Add API integration tests for event ingestion and incident actions, plus one end-to-end synthetic lunch-rush scenario. Every bug fix should include a regression test. Avoid live LLM calls in automated tests; use fixtures or fakes.

## Commit & Pull Request Guidelines

The repository has no commits from which to infer an existing convention. Use short, imperative subjects, optionally with a scoped conventional prefix, such as `feat(simulator): add lunch rush scenario`. Keep commits focused.

Pull requests should explain the behavior changed, testing performed, and any contract or schema impact. Link relevant issues or planning sections. Include screenshots for dashboard changes and sample payloads for API changes. Label all demo restaurant metrics as synthetic data.

## Security & Configuration

Keep secrets and provider credentials in ignored environment files; commit only sanitized examples such as `.env.example`. Validate all incoming events with typed schemas, and never log credentials or unredacted sensitive payloads.
