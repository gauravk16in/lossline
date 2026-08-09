# C07 — Forecast Evaluation and Acceptance Gate

Status: complete

## Goal

Evaluate baseline and GBT forecasts on repeated unseen future rows, persist complete per-row evidence, measure overall and subgroup behavior, evaluate interval coverage, and prevent an unqualified model from becoming accepted.

## Input

- C04 `DatasetRow` and point-in-time snapshots.
- C05 comparable-history baseline.
- C06 LightGBM artifact and forecast.
- Censored/missing outcome semantics.

## Output

- Typed per-forecast evaluation rows.
- Overall MAE, RMSE, WMAPE, bias, interval coverage and width.
- Outlet, SKU, service-window and demand-band comparisons.
- Expanding-window rolling-origin evaluator.
- Explicit `ACCEPTED`, `REJECTED` or `INSUFFICIENT_EVIDENCE` decision.
- Deterministic evaluation report ID.

## Files

- `packages/intelligence/src/lossline_intelligence/evaluation/forecast.py`
- `packages/intelligence/src/lossline_intelligence/evaluation/rolling.py`
- `packages/intelligence/src/lossline_intelligence/evaluation/__init__.py`
- `packages/intelligence/tests/test_forecast_evaluation.py`
- C06 residual-bound correction and dependency portability fixes.
- C07 documents and verification.

## Contracts

`ForecastEvaluationRow` aligns one baseline or GBT forecast with its matured actual at identical grain. It records model/forecast identity, training cutoff, as-of/window, prediction/bounds, actual/error, interval hit, demand band and status.

`ForecastMetricSummary` separates evaluated, censored and abstained counts and stores the required metrics.

`SubgroupComparison` pairs baseline/model summaries with relative WMAPE regression.

`ModelAcceptanceDecision` contains thresholds, overall improvement, failing subgroups and reasons.

`ForecastEvaluationReport` freezes rows, summaries, subgroups, acceptance and deterministic identity.

## Algorithm

1. Sort dataset rows chronologically.
2. Reserve an initial history; each later row becomes the next target.
3. Train/forecast baseline and GBT using only prior rows whose service windows
   fully ended by prediction as-of; concurrent SKU rows remain unavailable.
4. Assert every training cutoff is no later than prediction as-of.
5. Record censored outcomes without scoring them.
6. Calculate errors and interval hits for evaluable actuals.
7. Aggregate overall and four subgroup dimensions.
8. Require paired, equally sized baseline/model evidence and at least 5% relative
   overall WMAPE improvement.
9. Reject any subgroup above 10% relative WMAPE regression.
10. Return insufficient evidence when WMAPE cannot be evaluated.

## Assumptions

- Initial rolling history defaults to 25 rows because C06 requires at least 20 training rows after its internal holdout.
- WMAPE is the primary model-acceptance metric; MAE, RMSE and bias remain mandatory diagnostics.
- Every rolling target triggers retraining in C07; C19 may optimize scheduling without changing evaluation semantics.
- Interval coverage is observational and does not transform bounds into calibrated probabilities.

## Decisions

- Expanding-window rather than random or one-cutoff evaluation.
- Five-percent overall WMAPE improvement requirement.
- Ten-percent maximum subgroup regression.
- Censored outcomes recorded but excluded from accuracy.
- Zero-total actual demand yields unavailable WMAPE and insufficient acceptance evidence.
- Correct C06 signed-residual inversion when constructing demand bounds.

## Failure modes

- Future rows entering training.
- Concurrent, not-yet-matured service-window outcomes entering training.
- Censored actuals scored as demand.
- Overall improvement hiding subgroup harm.
- Empty or zero-denominator metrics treated as success.
- Baseline and model scored on different numbers of targets.
- Residual sign inversion creating invalid demand bounds.
- Non-repeatable evaluation identity.
- A rejected artifact loaded as production accepted model.

## Tests

- Exact overall metrics and interval diagnostics.
- Zero-demand WMAPE.
- Acceptance and below-threshold rejection.
- Subgroup regression rejection.
- Insufficient evidence.
- Mismatched baseline/model evaluation counts.
- Custom subgroup threshold behavior.
- Four required subgroup dimensions.
- Rolling-origin repeatability and cutoff safety.
- Concurrent-window exclusion.
- Censored outcome recording.
- Invalid configuration rejection.
- C06 focused and full regression suites.

## Integration points

C08/C09 may consume a GBT forecast only when C07 acceptance is `ACCEPTED`; otherwise C19 loads the baseline. C11 includes evaluation evidence in the dossier. C18 evaluates agent decisions independently. C21 appends matured actuals and recalculates operational reports.

## Definition of done

C07 is complete when expanding-window evaluation is real, every target has auditable records, required metrics/subgroups/coverage are computed, acceptance gates pass boundary tests, C06 runs on Python 3.12 locally, full regressions pass, and verification has no unresolved failure.
