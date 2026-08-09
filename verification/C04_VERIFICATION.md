# C04 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

Focused command:

```text
python -m pytest packages/intelligence/tests/test_feature_snapshot.py -v
```

Result: 37 passed.

Intelligence regression command:

```text
python -m pytest packages/intelligence/tests/ -q
```

Result: 255 passed (218 existing + 37 new).

Simulator regression command:

```text
python -m pytest simulator/tests/ -q
```

Result: 12 passed.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| FeatureSnapshot implementation | `features/snapshot.py` — frozen Pydantic model | PASS |
| Point-in-time dataset builder | `features/pipeline.py` — `build_dataset()` | PASS |
| Outlet × SKU × service-window rows | `test_multi_sku_rows` — 3 SKUs × 1 window = 3 rows | PASS |
| Lag features | `test_lag_populated_on_second_window` — lag from prior window | PASS |
| Calendar/context features | 6 context features extracted from window input | PASS |
| Future and late-record exclusion | `test_lag_excluded_when_prior_window_after_prediction` | PASS |
| Censored-demand target handling | `test_stockout_flagged`, `test_dataset_row_censored_flag` | PASS |
| Dataset fingerprint | `test_reproducible`, `test_different_data_different_fingerprint` | PASS |
| FeatureSnapshot contract frozen | Strict frozen Pydantic model with `extra="forbid"` | PASS |
| Snapshot fingerprint reproducible | `test_deterministic_fingerprint` | PASS |
| Dataset fingerprint reproducible | `test_golden_scenarios_dataset` — A–G stable | PASS |
| Future-record leakage test passing | `test_lag_excluded_when_prior_window_after_prediction` | PASS |
| Censored target test passing | `test_stockout_flagged` + `test_dataset_row_censored_flag` | PASS |
| Golden scenario coverage | `test_all_scenarios_produce_valid_snapshots` — A–G | PASS |
| Scenario E stockout | `test_scenario_e_stockout_censored` | PASS |
| Scenario G missing weather | `test_scenario_g_missing_weather` | PASS |
| Registry validation | `test_all_registered_features_present` | PASS |
| Missing feature tracking | `test_missing_rainfall`, `test_missing_lag_first_window` | PASS |
| Imputation tracking | `test_imputed_promotion_discount` | PASS |
| Quality completeness | `test_completeness_fraction` | PASS |
| Service window UTC | `test_dinner_window_utc`, `test_lunch_window_utc` | PASS |
| Input validation | `test_naive_window_start_rejected`, edge cases | PASS |
| Intelligence compatibility | Intelligence regression suite | 255 passed — PASS |
| Simulator compatibility | Simulator regression suite | 12 passed — PASS |

## Handoff gate

| Gate requirement | Status |
|---|---|
| C04 feature pipeline tests passing | 37/37 PASS |
| C04 verification status | PASS |
| FeatureSnapshot contract frozen | Frozen Pydantic model, `extra="forbid"` |
| Dataset fingerprint reproducible | `test_golden_scenarios_dataset` confirms stability |
| Future-record leakage test passing | `test_lag_excluded_when_prior_window_after_prediction` PASS |
| Censored target test passing | `test_stockout_flagged` + `test_dataset_row_censored_flag` PASS |

## Expected versus actual

Expected: a point-in-time feature pipeline producing typed, fingerprinted snapshots from C03 synthetic windows, with temporal safety and censored-demand handling.

Actual: 16 registered features covering calendar, weather, promotion, inventory, capacity, demand history, and SKU statics. Pipeline enforces future/late-record exclusion via prior_window_end vs prediction_as_of comparison. Censored targets are flagged but preserved. Dataset fingerprints are deterministic across runs. All golden scenarios A–G produce valid snapshots.

## Known limitations

- The pipeline does not import from the simulator; test helpers convert `SyntheticWindow` to pipeline input types.
- Rolling features (multi-window aggregates) are not implemented — only single-lag.
- No backend persistence, API endpoints, or frontend types introduced (C19 concern).
- Verified on the repository Python 3.12 environment. The C03→C04 simulator test path is explicit, so all 37 focused tests execute without skips.

## Manual checks

- Confirmed no new `restaurant_id` field.
- Confirmed no float-valued feature — all numerics use `Decimal` or `int`.
- Confirmed no mutable global registry state.
- Confirmed no domain model duplication — pipeline imports from `features/registry.py` (C02).
- Confirmed `FeatureSnapshot` uses `extra="forbid"` and `frozen=True`.
- Confirmed `DatasetRow` is a `@dataclass(frozen=True)`.
- Confirmed no backend, API, or frontend changes.

## Integration result

C04 provides the feature pipeline required by C05 for baseline/split construction and C06 for model training. Backend persistence and API adapters are deferred to C19. The reactive path is unchanged.

## Decision references

- C01 grain/time contracts.
- C02 signal and feature registries (ADR 0003).
- C03 synthetic causal world (ADR 0004).
