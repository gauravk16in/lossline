# ADR 0022 — Event-Only Seeded Predictive Demo

Status: accepted — 2026-08-09

## Decision

The predictive simulator emits only historical actuals, future-known scheduled inputs and later actuals through the canonical event API. It never emits forecasts, projections, risk scores, decisions or evaluations. Backend deterministic/model-owned code constructs the complete artifact chain, with an explicit baseline when no accepted loadable ML artifact exists.

The golden scenario uses a promotion-limited-inventory world because it produces an observable stockout decision and matured outcome while preserving latent-demand separation. Manager approval occurs through the same predictive review API used by the UI.

## Consequences

The demo validates architecture rather than replaying precomputed answers. Seed and event time fully determine artifact identities. The demo uses synthetic latent demand and therefore proves engineering behavior, not production accuracy or causal action impact.

## Verification

Envelope-content tests prohibit model outputs, E2E tests assert eight persisted events and the full artifact/evaluation counts, identical-run tests compare IDs, and a real Uvicorn/CLI run records the same summary.
