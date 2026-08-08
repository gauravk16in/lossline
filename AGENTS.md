# Repository Guidelines

## Project Structure & Module Organization

LOSSLine is currently in its planning stage. Treat `FINAL_IMPLEMENTATION_PLAN.md` as the implementation authority; `IMPLEMENTATION_PLAN.md` is the superseded candidate. The intended repository boundaries are:

- `apps/backend/`: FastAPI application, persistence models, and HTTP endpoints.
- `apps/frontend/`: operator dashboard and incident/action workflows.
- `services/intelligence/`: deterministic aggregation, anomaly detection, correlation, confidence scoring, and recommendations.
- `simulator/`: synthetic restaurant events and repeatable demo scenarios.
- `docs/`: architecture decisions, contracts, runbooks, and demo guidance created during implementation.

Keep the MVP a modular monolith. The frozen path is FastAPI → PostgreSQL/outbox → Redis Stream `restaurant.events` → deterministic detection → LangGraph investigation, with REST as authoritative UI state and WebSocket for transient live transitions. Do not bypass the real ingestion path in the simulator.

## Build, Test, and Development Commands

No build or test tooling is committed yet. Document setup in the root README and expose predictable commands such as `make dev`, `make test`, and `make lint`. Pin dependencies and commit lockfiles.

## Coding Style & Naming Conventions

For Python, use 4-space indentation, type annotations, `snake_case` for functions/modules, and `PascalCase` for classes and Pydantic models. Keep business calculations deterministic and side-effect free where practical. Numeric rules belong in versioned configuration; never present defaults as business facts.

For frontend code, use `PascalCase` for components and `camelCase` for variables and hooks. Add formatter and linter configuration with the first implementation.

## Testing Guidelines

Place tests near their package or in package-level `tests/`, using names such as `test_cancellation_detector.py`. Unit-test every deterministic rule. Integration tests cover the PostgreSQL outbox, Redis replay/idempotency, LangGraph resume, REST contracts, and WebSocket reconnect. Keep one seeded end-to-end lunch-rush scenario. Fake LLM calls in automated tests.

## Commit & Pull Request Guidelines

The history is too small to establish a reliable commit convention. Use short, imperative subjects, optionally with a scoped conventional prefix, such as `feat(simulator): add lunch rush scenario`. Keep commits focused.

Pull requests should explain changed behavior, tests, and contract/configuration/schema impact. Link the relevant final-plan section. Include screenshots for UI changes and payloads for API changes. Label demo metrics as synthetic, use uncertainty language, and distinguish estimated exposure from observed loss.

## Security & Configuration

Keep secrets and provider credentials in ignored environment files; commit only sanitized examples such as `.env.example`. Validate all incoming events with typed schemas, and never log credentials or unredacted sensitive payloads.
