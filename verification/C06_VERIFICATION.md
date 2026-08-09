# C06 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

C06 focused command:

```text
C:\Users\chand\AppData\Local\Programs\Python\Python311\python.exe -m pytest packages/intelligence/tests/test_forecast_gbt.py -v
```

Result: 13 passed in 6.01s.

Intelligence regression command:

```text
C:\Users\chand\AppData\Local\Programs\Python\Python311\python.exe -m pytest packages/intelligence/tests/ -q
```

Result: 339 passed in 1.43s.

Simulator regression command:

```text
C:\Users\chand\AppData\Local\Programs\Python\Python311\python.exe -m pytest simulator/tests/ -q
```

Result: 12 passed in 0.05s.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| LightGBM 4.6.0 pinned | pyproject.toml, `pip show lightgbm` | PASS |
| NumPy 2.2.3 pinned | pyproject.toml | PASS |
| Deterministic artifact_id | `test_artifact_id_is_deterministic` | PASS |
| Deterministic checksum | `test_artifact_id_is_deterministic` | PASS |
| training_cutoff = max(window_end) of training rows | `test_artifact_stores_training_cutoff` | PASS |
| Evaluation metrics finite and non-negative | `test_artifact_evaluation_metrics_are_finite`, `test_gbt_mae_finite_and_non_negative` | PASS |
| min_train_rows enforcement | `test_train_requires_minimum_rows` | PASS |
| Censored-row exclusion from training | `test_censored_rows_excluded_from_training` | PASS |
| feature_names sorted, non-empty, numeric-only | `test_feature_names_are_deterministic_and_numeric_only` | PASS |
| GBT test-fold metrics computed | `test_gbt_metrics_are_computed_on_test_fold` | PASS |
| Bounds contain point (lower ≤ point ≤ upper ≥ 0) | `test_forecast_produces_valid_bounds`, `test_residual_bounds_contain_point` | PASS |
| Forecast repeatability | `test_forecast_is_repeatable` | PASS |
| NO_ARTIFACT abstention | `test_no_artifact_abstains` | PASS |
| INVALID_TARGET_SNAPSHOT abstention | `test_target_window_before_as_of_abstains` | PASS |
| Bounds labelled empirical_residual_80.v1 (not probability) | Versioned constant in gbt.py | PASS |
| Full intelligence compatibility | 339 passed — no regressions | PASS |
| Simulator compatibility | 12 passed — no regressions | PASS |

## Expected versus actual

Expected: a versioned gradient-boosted tabular model trained with chronological safety, producing deterministic artifacts, valid empirical bounds, and typed abstentions.

Actual: `train_gbt_model()` returns a deterministic `MLForecastArtifact` with pinned LightGBM 4.6.0; `forecast_gbt()` produces `GBTForecast` with containment-guaranteed bounds or typed `GBTAbstention`; all 13 C06 tests pass; no intelligence or simulator regressions.

## Known limitations

- Empirical bounds use training-fold residual dispersion, not calibrated test-fold quantiles. C07 owns formal coverage measurement.
- The `DEFAULT_TEST_FRACTION = 0.20` single held-out split does not yet implement full per-row rolling-origin evaluation. C07 extends this.
- String feature encoding (one-hot, ordinal) is not implemented; string features are silently excluded from `feature_names`. If new registry features are strings, they need encoding before they can contribute to model predictions.
- `MLForecastArtifact._booster` is an in-process object only. C19 owns serializing and loading the booster from storage (`booster.model_to_string()` / `lgb.Booster(model_str=...)`).
- WMAPE is omitted from `evaluation_metrics` when total actual test demand is zero; callers must handle its absence.

## Manual checks

- Confirmed artifact_id is identical on two independent training runs with the same dataset.
- Confirmed no LLM call, no DB/Redis access, no process-global mutable state.
- Confirmed bounds are never labelled as probability intervals in code or tests.
- Confirmed `feature_names` excludes the `weather_state` string feature from demo registry.
- Confirmed `evaluation_metrics["mae"]` is a finite, non-negative Decimal.
- Confirmed residual_p10 / residual_p90 values are finite Decimal.

## Integration result

C06 produces the `MLForecastArtifact` and `GBTForecast` contracts required by C07 for acceptance evaluation. It changes no backend, database, simulator runner or frontend behavior.

## Decision references

- RE-004 — ACCEPTED C06 (LightGBM 4.6.0).
- RE-005 — ACCEPTED C06 (rolling-origin chronological split, 20 % held-out test).
- RE-007 — ACCEPTED C06 (empirical residual 10th/90th percentile bounds, `empirical_residual_80.v1`).
- ADR 0006.
