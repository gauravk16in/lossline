# ADR 0005: Comparable-history demand baseline

Status: accepted — 2026-08-09

## Problem

LOSSLine needs a reproducible demand benchmark before an ML model can be considered. The reactive baseline compares operational anomaly metrics and fills missing history with fixtures; it is not suitable for future outlet × SKU demand. A baseline must also avoid stockout-censored targets and future records.

## Options

1. Last observed demand.
2. Rolling mean over all recent demand.
3. Median over comparable weekday/service-window history with deterministic sparse backoff.

## Decision

Adopt option 3. Use only uncensored rows whose windows ended by `prediction_as_of` and started before the target window. Require four observations at a scope. Search scopes in order:

1. outlet × SKU × weekday × service window;
2. SKU × weekday × service window;
3. outlet × category × weekday × service window;
4. category × weekday × service window;
5. global weekday × service window;
6. global history.

Category backoff is used only when the caller supplies an explicit catalog mapping. If no scope has four samples, return a typed abstention. Emit empirical 10th/90th comparable-demand bounds targeting an 80% descriptive range; do not label them probabilities.

## Consequences

The baseline is robust and explainable, remains useful as a production fallback, and exposes sparse-history limitations. Broad backoff may reduce local specificity, so the selected scope and source snapshots are included in every forecast. C07 will evaluate interval coverage and subgroup behavior.

## Verification

- Below/at/above history threshold.
- Censored and future-history exclusion.
- Every backoff level.
- Repeatable IDs, points and bounds.
- Rolling MAE, RMSE, WMAPE and bias.
- Explicit WMAPE absence when total actual demand is zero.

