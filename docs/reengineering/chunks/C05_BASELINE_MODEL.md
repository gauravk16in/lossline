# C05 — Comparable-History Baseline Model

Status: complete

## Goal

Produce the first honest demand forecast benchmark at outlet × SKU × named service-window grain, with chronological safety, censored-target exclusion, deterministic sparse backoff, empirical bounds, abstention and rolling metrics.

## Input

- C04 `FeatureSnapshot` and `DatasetRow` contracts.
- C01 predictive grain and uncertainty separation.
- C03 censored latent-demand outcomes.
- Optional explicit SKU-to-category catalog mapping.

## Output

- `BaselineForecast` validated serialization boundary.
- `BaselineAbstention` for inadequate or invalid inputs.
- Comparable-history selection and backoff algorithm.
- Empirical descriptive demand bounds.
- Rolling baseline MAE, RMSE, WMAPE and bias.
- ADR 0005, tests and verification evidence.

## Files

- `packages/intelligence/src/lossline_intelligence/forecasts/baseline.py`
- `packages/intelligence/src/lossline_intelligence/forecasts/__init__.py`
- `packages/intelligence/tests/test_forecast_baseline.py`
- C05 documentation and verification.

## Contracts

`BaselineForecast` contains deterministic forecast ID/version, interval method, prediction as-of, canonical grain/window, feature-snapshot reference, point/lower/upper demand, selected comparison scope, sample count, source snapshot IDs and sufficiency.

`BaselineAbstention` contains the target snapshot, reason, available eligible history and required history.

`BaselineMetrics` contains forecast/abstention counts and optional MAE, RMSE, WMAPE and bias. WMAPE is `None` when aggregate actual demand is zero.

## Algorithm

1. Reject naive as-of time and invalid minimum history.
2. Require the target window not to have started before prediction as-of.
3. Exclude censored, negative, future-ending and non-historical rows.
4. Try comparison scopes in ADR 0005 order.
5. Select the first scope with at least four eligible observations.
6. Calculate point demand as the median.
7. Calculate linearly interpolated 10th/90th historical-demand quantiles and ensure they contain the point.
8. Persist scope and every source snapshot ID.
9. Abstain explicitly when no scope is sufficient.

Rolling evaluation sorts targets chronologically, forecasts each uncensored row using only earlier rows, and calculates required metrics over successful forecasts.

## Assumptions

- Four comparable uncensored observations is the initial CONFIG_DEFAULT minimum.
- Empirical bounds describe comparable historical demand dispersion and are not probabilities.
- SKU category identity comes from an explicit catalog mapping and is never inferred from SKU text.
- C07 owns formal baseline evaluation artifacts, interval coverage and acceptance reporting.

## Decisions

- Median rather than mean or last-value baseline.
- Fixture-filled reactive history is prohibited.
- Censored rows never enter baseline calculation.
- All backoff levels retain weekday and service-window comparability until the final global fallback.
- Global fallback still requires minimum evidence.
- Baseline remains an available fallback after ML introduction.

## Failure modes

- Future or target-window leakage.
- Stockout-censored demand entering history.
- Cross-category backoff without catalog evidence.
- Silent zero forecast on sparse history.
- Duplicate or untraceable evidence IDs.
- Bounds presented as calibrated probability intervals.
- WMAPE division by zero.

## Tests

- Repeatability, median and empirical bounds.
- Below- and at-threshold history.
- Censored-history exclusion.
- Future-history exclusion.
- SKU, category, weekday/window and global backoff.
- Invalid target/as-of and minimum-history rejection.
- Rolling MAE, RMSE, WMAPE and bias.
- Zero-total actual WMAPE behavior.
- Full intelligence and simulator regression suites.

## Integration points

C06 benchmarks the first ML model against this forecast contract. C07 persists and compares rolling-origin evaluation. C08/C09 consume lower/point/upper demand. C11 includes scope, historical performance and source evidence in the dossier. C19 loads this baseline when no accepted ML artifact is available.

## Definition of done

C05 is complete when deterministic forecasts and abstentions are implemented, chronology/censoring/backoff tests pass, required baseline metrics are computed, C04 executes all integration tests without skips, full regression suites pass, and verification contains no unresolved failure.

