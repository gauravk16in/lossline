# C0 — Predictive Architecture and Contract Freeze

Status: complete

> Mapping notice: this pre-reengineering C0 artifact is preserved as source evidence. Its architecture responsibility is now owned by `docs/reengineering/chunks/C01_ARCHITECTURE_AND_CONTRACTS.md` under ADR 0002. Conflicts are resolved in favor of the C01 contract; implementation-specific C0 defaults remain proposals unless accepted in `docs/reengineering/DECISIONS.md`.

## Goal

Freeze the vocabulary, ownership boundaries, MVP prediction contract, and migration path needed before predictive code is added.

## Frozen MVP contract

- The prediction grain is `outlet_id × sku_id × named service window`.
- Named service windows are outlet-local half-open intervals. The MVP windows are configuration, not enums; the demo starts with `LUNCH`.
- A forecast is made at 10:00 outlet-local time for the same day's lunch window. All persisted timestamps remain timezone-aware UTC.
- Demand means latent requested SKU quantity. Observed sales are a separate outcome. Stockout-affected windows are censored and are never silently labeled as demand.
- SKU identity is catalog-versioned. Bundles and modifiers are expanded to component SKUs before dataset construction. Substitutions remain distinct SKUs for the MVP.
- Inventory uses each SKU's catalog base unit. Conversions require an explicit, versioned conversion rule; no implicit conversions are permitted.
- The baseline comparison order is outlet/SKU/weekday/window, SKU/weekday/window, outlet/category/weekday/window, then global category/weekday/window. A level needs four uncensored observations.
- Model acceptance uses rolling-origin WMAPE as the primary metric and requires at least 5% relative improvement over the accepted baseline, with no outlet or demand-band WMAPE regression greater than 10%.
- Forecast intervals target 80% empirical coverage. They are bounds, not probabilities.
- Knowledge time is `observed_at`. A record is usable only when both `observed_at` and provenance `ingested_at` are no later than `prediction_as_of`. Late records remain available for replay but not for the original snapshot.
- Forecast weather must retain provider issue/vintage time. Actual weather is outcome data and is not forecast-safe.
- Holidays, festivals, promotions, and local events must be registered, source-versioned signals whose publication time is known.
- C2 owns synthetic causal assumptions and scenario parameter freezes.
- Inventory safety buffer, capacity formulas, decision rounding/limits, confidence representation, attribution wording, historical similarity, orchestration lifecycle, and outcome maturity are frozen by their owning chunks C7–C17, before their implementation.
- Structured PostgreSQL retrieval precedes document retrieval. A vector store requires a measured retrieval failure and a real unstructured corpus.
- Artifacts are immutable files plus a persisted manifest containing cutoff, data fingerprint, registry/code version, parameters, metrics, and checksum. Deployment selects a manifest; it never overwrites an artifact.
- Predictive raw data, normalized signals, feature snapshots, forecasts, and outcomes are retained for deterministic replay in the MVP. A production deletion policy is required before non-synthetic data.
- The demo scope is one configured Asia/Kolkata outlet, a versioned SKU catalog, and a lunch service window; contracts are multi-outlet.

## Terminology

`RawEvent` is the source payload retained for audit. `NormalizedSignal` is a registry-validated observation with knowledge time, effective time, quality, and provenance. `ReactiveSignal` is the existing detector output currently named `Signal`. `FeatureSnapshot` is the immutable point-in-time input to one forecast. `Forecast` predicts future latent demand. `Risk` compares forecasts with operational supply. `DecisionCandidate` is deterministic advice; it is not an autonomous action.

New predictive code must use `NormalizedSignal` and must not import the detector `Signal` under that unqualified name. Renaming the existing public class now would break the functioning reactive path, so its compatibility contract remains intact through migration.

## Ownership and coexistence

- `packages/intelligence/` owns contracts, registries, datasets, forecasts, projections, risks, attribution, decisions, and evaluation.
- `apps/backend/src/intelligence/` owns repositories, orchestration, artifact loading, persistence, and workflow integration.
- PostgreSQL is durable truth; Redis is transport and notification only.
- The simulator uses normal ingestion APIs.
- The LLM may express grounded prose only and owns no numeric result.
- The reactive incident pipeline remains operational during C1–C17. Predictive APIs and persistence are additive. Reactive signals later become residual/real-time evidence; removal requires parity evidence and a separate decision.

## C0 gate

C0 passes when this contract and its decision record exist, the superseded plan is not used as implementation authority, and C1 can add contracts without changing the reactive API.
