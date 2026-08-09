# C04 — Feature Pipeline

Status: complete

## Goal

Convert C03 synthetic window outcomes into point-in-time feature snapshots and dataset rows using C02 registries, with deterministic fingerprints, future/late-record exclusion, and censored-demand target handling.

## Input

- C01 grain/time contracts (outlet × SKU × named service window).
- C02 signal and feature registries (semantic validation, fingerprints).
- C03 synthetic causal world (golden scenarios A–G).

## Output

- `FeatureSnapshot` Pydantic serialization boundary with typed feature values.
- `SnapshotQuality` quality metadata (completeness, censoring, data quality).
- `DatasetRow` training record with target and censoring flag.
- `ServiceWindowConfig` for named service window UTC resolution.
- Demo feature catalog with 16 registered features.
- `build_snapshot()` and `build_dataset()` pure functions.
- Deterministic snapshot and dataset fingerprints.
- C04 tests and verification evidence.

## Files

- `packages/intelligence/src/lossline_intelligence/features/snapshot.py`
- `packages/intelligence/src/lossline_intelligence/features/windows.py`
- `packages/intelligence/src/lossline_intelligence/features/catalog.py`
- `packages/intelligence/src/lossline_intelligence/features/pipeline.py`
- `packages/intelligence/src/lossline_intelligence/features/__init__.py`
- `packages/intelligence/tests/test_feature_snapshot.py`
- C04 documentation and verification.

## Contracts

`FeatureSnapshot` is a strict frozen Pydantic model carrying snapshot identity, pipeline version, prediction-as-of, grain (outlet, SKU, service window), temporal boundaries, registry version and fingerprint, typed feature values, source signal IDs, missing/imputed feature lists, quality metadata, and a deterministic content fingerprint.

`DatasetRow` is a frozen dataclass pairing a `FeatureSnapshot` with a latent-demand target, observed (potentially censored) demand, and a censoring flag.

`WindowFeatureInput` and `SkuFeatureInput` are frozen dataclasses defining the pipeline's input contract, independent of the simulator. Callers convert data-source-specific types to these inputs.

`ServiceWindowConfig` resolves named service windows in outlet timezone to UTC half-open intervals.

The demo catalog registers 16 features across calendar, weather, promotion, inventory, capacity, demand history, and SKU static categories.

## Algorithm

For each outlet × SKU × window:

1. Extract context features from the window input (weekday, weather, holiday, delivery share, etc.).
2. Extract per-SKU features (opening inventory, promotion status, base demand, workload).
3. Apply future/late-record exclusion: only include lag features from windows that ended before `prediction_as_of`.
4. Apply missing-value strategy per registry definition (EXPLICIT_MISSING or IMPUTE_CONSTANT).
5. Validate each feature value against its registered data type.
6. Compute quality metadata: completeness ratio, data sufficiency, censoring status.
7. Compute deterministic SHA-256 fingerprint from sorted feature values, pipeline version, and registry fingerprint.
8. Compute deterministic snapshot ID from grain, temporal coordinates, and pipeline version.
9. Return a frozen `FeatureSnapshot`.

For multi-window datasets:

1. Process windows in order, tracking prior fulfilled quantities per outlet × SKU.
2. Populate lag features from the immediately preceding window's fulfilled quantity.
3. Enforce temporal safety: lag data from windows ending after `prediction_as_of` is excluded.
4. Build a `DatasetRow` for each window × SKU with latent demand as target and stockout as censoring flag.
5. Compute the dataset fingerprint from ordered snapshot fingerprints, targets,
   observed quantities, and censoring state.

## Assumptions

- Pipeline input types are independent of the simulator; conversion happens at call sites.
- Lag features use fulfilled (observable) demand from the prior window, not latent demand.
- Censored rows (stockout) are flagged but included in the dataset; C05/C06 own target construction.
- Promotion discount is imputed to zero for non-promoted SKUs (IMPUTE_CONSTANT).
- No backend persistence or API introduced; C19 owns adapters.

## Decisions

- One `FeatureSnapshot` per outlet × SKU × service window (C01 grain).
- Pipeline does not import from the simulator; test helpers convert `SyntheticWindow`.
- Feature values stored as native Python types in a keyed dict.
- Bool is checked before int in type validation to avoid Python subclass coercion.
- `created_at` is excluded from fingerprint computation.
- Dataset fingerprint hashes ordered features plus label and censoring state, so
  a model artifact cannot keep the same identity after its training labels change.

## Failure modes

- Naive (no timezone) timestamps on prediction_as_of or window boundaries.
- Inverted window (end before start) or empty SKU inputs.
- Feature value type mismatch against registry definition.
- Non-finite Decimal feature values.
- Empty categorical feature values.
- Unregistered feature IDs.

## Tests

- Deterministic fingerprint for identical inputs.
- Fingerprint sensitivity to changed feature values.
- Bool/int type distinction in fingerprint encoding.
- Snapshot ID determinism and grain sensitivity.
- Registry validation: all registered features present.
- Missing rainfall tracked as missing feature.
- Missing lag on first window.
- Imputed promotion discount on non-promoted SKU.
- Data sufficiency false when features missing; true when complete.
- Censored target flagged on stockout.
- DatasetRow carries separate target and observed quantities.
- Future lag excluded when prior window ends after prediction_as_of.
- Lag included when prior window ends before prediction_as_of.
- Lag at boundary (exactly at prediction_as_of) included.
- Naive prediction_as_of rejected.
- Quality completeness fraction and data quality score.
- Service window UTC resolution for DINNER and LUNCH.
- Invalid timezone rejected.
- Inverted service window rejected.
- Golden scenarios A–G all produce valid snapshots.
- Scenario E stockout produces censored target.
- Scenario G missing weather produces missing rainfall.
- Multi-window row count and lag population.
- Multi-SKU row count.
- Dataset fingerprint reproducibility.
- Dataset fingerprint sensitivity to changed data.
- Dataset fingerprint sensitivity to changed targets, observations, and censoring.
- Full golden scenario dataset fingerprint stability.
- Naive and inverted window inputs rejected.
- Empty SKU inputs rejected.

## Integration points

- C05 consumes feature snapshots for baseline and train/test split construction.
- C06 model artifacts reference the feature registry fingerprint from snapshots.
- C08/C09 use prediction features alongside inventory/capacity projections.
- C11 dossier provenance references source snapshots.
- C19 persists snapshots to PostgreSQL and exposes them via API.
- C22 runs integrated scenarios using the full pipeline.

## Definition of done

C04 is complete when feature pipeline tests pass, snapshot and dataset fingerprints are reproducible, future/late-record exclusion is proven, censored-demand targets are handled, the demo catalog validates against the registry, golden scenarios A–G produce valid snapshots, the existing intelligence and simulator test suites remain green, and verification records no unresolved failure.
