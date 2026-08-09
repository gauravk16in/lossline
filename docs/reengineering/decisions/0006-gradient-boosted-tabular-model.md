# ADR 0006: Gradient-boosted tabular demand model

Status: accepted — 2026-08-09

## Problem

C05 established the comparable-history median as an honest baseline. C06 must introduce the first ML model and demonstrate it can improve on the baseline under realistic deployment conditions (no future leakage, realistic sparse histories). Three decisions deferred from C01 must be frozen:

- **RE-004**: Which ML library and artifact format?
- **RE-005**: How should the train/evaluation time split be structured?
- **RE-007**: How should forecast uncertainty be represented?

## Options

### RE-004 — ML library

1. Linear regression (scikit-learn) — interpretable but limited non-linearity.
2. Gradient-boosted tabular regressor (LightGBM or XGBoost) — suited for mixed tabular factors and MVP data volume; portable artifacts.
3. Deep sequence model (PyTorch/TensorFlow) — high expressive capacity but requires much more data and infrastructure.

### RE-005 — Time split

1. Random train/test split — leaks future data; unacceptable.
2. Fixed chronological split at a single cutoff — simulates one deployment point.
3. Rolling-origin chronological evaluation with final held-out test period — measures deployment-like performance across multiple forecast horizons.

### RE-007 — Uncertainty representation

1. Model-internal confidence (e.g., Gradient Boosted quantile regression) — requires separate quantile models per percentile.
2. Parametric Gaussian fit to residuals — assumes normality; untested.
3. Empirical residual bounds from training-fold signed errors — non-parametric, auditable, describes observed dispersion without probability claims.

## Decisions

**RE-004**: Adopt **LightGBM 4.6.0**, pinned. Reasons:
- Handles mixed numeric/boolean tabular features without encoding preprocessing.
- Produces a portable model string artifact (`booster.model_to_string()`).
- No dependency on scikit-learn; minimal Python 3.11 surface area.
- Single-file installation; no C extension build required on Windows.

**RE-005**: Adopt **rolling-origin chronological split**: sort eligible (uncensored) rows by `window_start`; use first `(1 - test_fraction)` as training, final `test_fraction` as held-out test. Default `test_fraction = 0.20`. Reasons:
- Prevents future leakage by construction.
- The test set represents deployment-like unseen windows.
- C07 will extend to full rolling-origin (per-row evaluation); C06 uses a single split for MVP tractability.

**RE-007**: Adopt **empirical residual 10th/90th percentile bounds** from training-fold signed errors (residual = pred − actual), versioned as `empirical_residual_80.v1`. Reasons:
- Non-parametric; no distributional assumption.
- Bounds describe observed training dispersion, not calibrated probability intervals.
- Labels explicitly prevent misrepresentation as confidence intervals.
- C07 will evaluate subgroup coverage and width.

## Artifact format

`MLForecastArtifact` stores:
- Deterministic `artifact_id` (SHA-256 of training_cutoff, dataset_fingerprint, registry_fingerprint, code_version, params_fingerprint).
- `checksum`: SHA-256 of `booster.model_to_string()` for integrity checking.
- `params` and `params_fingerprint`: reproduce training exactly.
- `feature_names`: registry-aligned, sorted, numeric/boolean only.
- `evaluation_metrics`: MAE, RMSE, WMAPE, bias on held-out test fold.
- `residual_p10`, `residual_p90`: signed `prediction - actual` residual quantiles; inference converts them back to demand bounds by subtraction.

## Acceptance gate

C06 requires: `artifact.evaluation_metrics["mae"]` is a finite, non-negative Decimal on the held-out test fold. C07 owns the formal threshold (must beat baseline MAE by a defined margin) and interval coverage acceptance.

## Consequences

- `lightgbm==4.6.0`, `numpy==2.2.3`, and its direct runtime dependency `scipy==1.18.0` are pinned production dependencies. macOS development also requires the system OpenMP runtime (`brew install libomp`).
- `MLForecastArtifact` is an internal `@dataclass(frozen=True)`, not a Pydantic model — no validation overhead for an in-process object.
- `GBTForecast` is a Pydantic `BaseModel` (serialization boundary, C01 contract).
- The baseline remains available as a fallback when no accepted ML artifact exists (C19).
- Changing `params`, `feature_names`, or `training_cutoff` produces a different `artifact_id`, making artifact drift mechanically detectable.

## Verification

- Deterministic artifact IDs across two identical training runs.
- Held-out test fold MAE is finite and non-negative.
- All forecast bounds satisfy `lower ≤ point ≤ upper ≥ 0`.
- Censored rows excluded from training and test.
- No string features in `feature_names`.
- Repeatable forecasts given the same artifact and target snapshot.
