# ADR 0007: Rolling forecast evaluation and model acceptance

Status: accepted — 2026-08-09

## Problem

A single chronological holdout is insufficient to establish deployment-like behavior, subgroup safety, or interval quality. C06 can train a model, but the model must not become the accepted production forecast merely because one MAE value is finite.

## Decision

Use expanding-window rolling-origin evaluation. After an initial history, each chronological target is forecast using only rows whose service window fully ended by prediction as-of. Ordering alone is insufficient because concurrent outlet/SKU rows do not yet have matured outcomes. Record baseline and GBT predictions, actuals, errors, interval hits, abstentions, censoring and training cutoff at identical grain.

The primary acceptance metric is WMAPE. Accept the GBT only when:

- it improves overall WMAPE by at least 5% relative to the comparable-history baseline;
- no outlet, SKU, service-window or demand-band subgroup regresses by more than 10% relative WMAPE; and
- both baseline and model have evaluable, non-zero-denominator WMAPE.

Otherwise reject or return `INSUFFICIENT_EVIDENCE`. Censored outcomes are recorded but not scored. Bounds are assessed by empirical coverage and mean width; they remain descriptive rather than probabilistic.

## Consequences

Training is more expensive because the model is retrained for every origin. A model can improve globally and still fail subgroup safety. Zero-demand sets cannot decide WMAPE acceptance and require other evidence in later evaluation work.

## Verification

- Exact MAE, RMSE, WMAPE, bias, coverage and width tests.
- Five-percent acceptance boundary.
- Ten-percent subgroup regression rejection.
- Expanding-window cutoff never after prediction as-of.
- Concurrent, not-yet-matured rows excluded from model history.
- Censored outcome recording without scoring.
- Repeatable evaluation records and report IDs.
