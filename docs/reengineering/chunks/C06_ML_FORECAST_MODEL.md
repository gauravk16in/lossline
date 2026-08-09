# C06 — Gradient-Boosted Tabular Demand Forecast Model

Status: complete

## Goal

Implement the first ML demand forecast model at outlet × SKU × named service-window grain. Train a version-pinned gradient-boosted tabular regressor with rolling-origin chronological safety, deterministic artifact provenance, empirical residual bounds, and held-out test evaluation. Freeze decisions RE-004, RE-005 and RE-007.

## Input

- C04 `FeatureSnapshot` and `DatasetRow` contracts.
- C05 `BaselineForecast` for comparison reference (C07 owns the acceptance gate).
- C01 predictive grain, temporal safety and uncertainty-separation contracts.
- `compute_dataset_fingerprint` from `features/snapshot.py`.

## Output

- `MLForecastArtifact` — versioned, immutable model artifact with training metadata, evaluation metrics and residual bound parameters.
- `GBTForecast` — Pydantic serialization boundary for one per-grain forecast.
- `GBTAbstention` — explicit abstention when no artifact or temporal violation.
- `GBTAbstentionReason` — `StrEnum`: `NO_ARTIFACT`, `INVALID_TARGET_SNAPSHOT`.
- `train_gbt_model()` — rolling-origin training and evaluation function.
- `forecast_gbt()` — single-snapshot inference against a loaded artifact.
- ADR 0006, tests and verification evidence.

## Files

- `packages/intelligence/src/lossline_intelligence/forecasts/gbt.py`
- `packages/intelligence/src/lossline_intelligence/forecasts/__init__.py` (updated)
- `packages/intelligence/tests/test_forecast_gbt.py`
- `packages/intelligence/pyproject.toml` (lightgbm==4.6.0, numpy==2.2.3 added)
- C06 documentation and verification.

## Contracts

`MLForecastArtifact` (`@dataclass(frozen=True)`) contains deterministic `artifact_id`, `model_version`, `training_cutoff`, `dataset_fingerprint`, `registry_fingerprint`, `code_version`, `params`, `params_fingerprint`, `feature_names`, `evaluation_metrics`, `residual_p10`, `residual_p90`, `checksum`, `created_at`, and the internal `_booster` (excluded from comparisons).

`GBTForecast` (`BaseModel`, frozen) contains `forecast_id`, `model_version`, `artifact_id`, `interval_method`, `prediction_as_of`, canonical grain/window, `feature_snapshot_id`, `point_demand`, `lower_demand`, `upper_demand`, `data_sufficient`.

`GBTAbstention` (`@dataclass(frozen=True)`) contains `feature_snapshot_id`, `reason`, `artifact_id | None`.

## Algorithm

### Training (`train_gbt_model`)

1. Exclude censored rows from the eligible set.
2. Sort eligible rows chronologically by `window_start`.
3. Return `None` when `len(train_rows) < min_train_rows` (default: 20).
4. Split: first `(1 - test_fraction)` rows → training; remainder → held-out test.
5. Derive `feature_names`: sorted, numeric/boolean features only; string features are excluded.
6. Build NumPy matrices; train LightGBM booster with pinned `DEFAULT_PARAMS`.
7. Compute training-fold signed residuals (pred − actual); extract 10th/90th percentile → `residual_p10`, `residual_p90`.
8. Evaluate on held-out test fold: MAE, RMSE, WMAPE, bias. WMAPE is omitted when total actual demand is zero.
9. Assemble `MLForecastArtifact` with deterministic `artifact_id` and SHA-256 `checksum` of the booster string.

### Inference (`forecast_gbt`)

1. Return `GBTAbstention(NO_ARTIFACT)` when artifact is `None`.
2. Return `GBTAbstention(INVALID_TARGET_SNAPSHOT)` when `target.window_start < prediction_as_of`.
3. Extract feature vector in `artifact.feature_names` order.
4. Predict with booster; clamp raw prediction to ≥ 0.
5. Apply `residual_p10`/`residual_p90` as additive offsets to raw prediction.
6. Clamp bounds to ≥ 0; enforce containment: `lower ≤ point ≤ upper`.
7. Return `GBTForecast`.

## Assumptions

- 20 uncensored rows is the `MIN_TRAIN_ROWS` default — chosen to allow model fitting while failing fast on sparse histories.
- `DEFAULT_TEST_FRACTION = 0.20` — the final 20 % of rows (by `window_start`) form the held-out test period.
- `DEFAULT_PARAMS` seeds are fixed at `42`; output is deterministic for identical inputs.
- String features in `feature_values` are not usable without encoding and are silently excluded from `feature_names`.
- `residual_p10` is typically negative (model over-predicts) and `residual_p90` typically positive; both are applied symmetrically as offsets to the raw prediction.
- C07 owns formal baseline-vs-model acceptance, subgroup analysis and interval coverage evaluation.
- C19 owns artifact persistence and fallback logic (load baseline when no accepted ML artifact exists).

## Decisions

- LightGBM 4.6.0, pinned (RE-004 ACCEPTED).
- Rolling-origin chronological split, 20 % held-out test (RE-005 ACCEPTED).
- Empirical residual 10th/90th percentile bounds, labelled `empirical_residual_80.v1` (RE-007 ACCEPTED).
- `MLForecastArtifact` is an internal dataclass; `GBTForecast` is the serialization boundary.
- `artifact_id` is deterministic; changing params, features or training data produces a detectable new ID.

## Failure modes

- Future-data leakage through an incorrect split boundary.
- Censored-demand entering training targets.
- String features silently contributing to the model if the exclusion logic is bypassed.
- Non-deterministic booster output from un-pinned seeds.
- `checksum` mismatch indicating artifact corruption or substitution.
- Bounds presented as calibrated probability intervals.
- WMAPE computed when total actual demand is zero (explicit `None` guards this).

## Tests

- Minimum-rows enforcement (returns `None`).
- Artifact ID and checksum determinism.
- Training cutoff value correctness.
- Evaluation metrics finiteness and non-negativity.
- Per-row forecast bound containment.
- Forecast repeatability.
- `NO_ARTIFACT` and `INVALID_TARGET_SNAPSHOT` abstention paths.
- Censored-only dataset → `None`.
- `feature_names` sorted, non-empty, numeric-only.
- GBT MAE finite and non-negative on test fold.

## Integration points

C07 persists `MLForecastArtifact` evaluation metrics and runs formal baseline-vs-model acceptance. C08/C09 consume `GBTForecast` lower/point/upper demand. C11 includes model version and evaluation evidence in the dossier. C19 loads a persisted accepted ML artifact or falls back to baseline.

## Definition of done

C06 is complete when: all C06 tests pass, `artifact_id` is deterministic across two identical runs, `MLForecastArtifact` fields satisfy all contract invariants, full intelligence regression suite passes, simulator regression passes, and C06_VERIFICATION.md contains no unresolved failure.
