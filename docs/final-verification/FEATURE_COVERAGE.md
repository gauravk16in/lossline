# Predictive Feature Coverage

Verified on 2026-08-09 against the canonical `predictive.window_scheduled` event path.
The authoritative registry is `demo.v1`; persisted snapshots carry the registry's
SHA-256 fingerprint. Decimal JSON values are strings so precision is not lost.

## Runtime path

`POST /api/v1/events` → `EventEnvelope` validation → `WindowFeatureInput` /
`SkuFeatureInput` normalization → `build_snapshot()` registry validation →
`predictive_feature_snapshots.payload` → forecast by `feature_snapshot_id` →
`GET /api/v1/predictive/today/...feature_snapshots` → typed React contract.

The backend E2E test compares the complete persisted feature dictionary with the
values below. It also reads the same snapshot through
`GET /api/v1/predictive/features/{snapshot_id}` and compares its fingerprint.

## Every registered feature

| Feature | Source/raw contract | Normalized type/unit | Observed stored value | Baseline | GBT input | Decision/driver | Frontend |
|---|---|---|---:|---|---|---|---|
| `context.weekday` | scheduled context `weekday` | integer, ISO weekday | `5` | comparison scope | yes | eligible | typed snapshot |
| `context.service_window` | scheduled `service_window` | category, window name | `DINNER` | comparison scope | categorical excluded in GBT v1 | eligible | typed snapshot |
| `context.is_holiday` | scheduled context `holiday` | boolean flag | `false` | no | yes | eligible | typed snapshot |
| `context.local_event` | scheduled context `local_event` | boolean flag | `false` | no | yes | eligible | typed snapshot |
| `context.delivery_share` | scheduled context `delivery_share` | Decimal ratio | `0.6800` | no | yes | eligible | typed snapshot |
| `context.data_quality` | scheduled `data_quality` | Decimal score | `1.0000` | no | yes | dossier quality | typed snapshot |
| `weather.state` | scheduled weather forecast vintage | category, weather state | `RAIN` | no | categorical excluded in GBT v1 | eligible | typed snapshot |
| `weather.rainfall_mm` | scheduled weather forecast vintage | Decimal millimetres | `18.0000` | no | yes | eligible | typed snapshot |
| `promotion.active` | scheduled promoted SKU identity | boolean flag | `true` | no | yes | eligible | typed snapshot |
| `promotion.discount_pct` | scheduled promotion context | Decimal ratio | `0.2000` | no | yes | displayed driver | typed snapshot and driver value |
| `inventory.opening_quantity` | scheduled SKU plan | integer portions | `45` | no | yes | inventory projection | typed snapshot and projection |
| `capacity.available_minutes` | scheduled capacity plan | Decimal minutes | `1000.0000` | no | yes | capacity projection | typed snapshot and projection |
| `demand.fulfilled_quantity.lag1` | most recent matured prior window | integer portions | `51` | historical rows directly | yes | eligible | typed snapshot |
| `sku.base_demand` | scheduled SKU catalog input | Decimal portions | `52.0000` | no | yes | eligible | typed snapshot |
| `sku.workload_minutes` | scheduled SKU catalog input | Decimal minutes | `8.0000` | no | yes | capacity projection | typed snapshot |

“Eligible” means deterministic attribution may expose the feature when an
attribution candidate exists. The UI does not display every available context
field as a driver. It displays only persisted `DriverEvidence` records and shows
the exact feature value from the referenced persisted snapshot. It never invents
driver percentages.

## Leakage controls

- Target fields (`actual_demand`, fulfilled/unfulfilled quantities, stockout and
  ending inventory) belong only to `demand.window_observed` and `DatasetRow`.
- They are prohibited from the scheduled forecast envelope by the simulator test.
- Lag demand is populated only when the prior window ended at or before
  `prediction_as_of`.
- Forecast-vintage weather and scheduled promotion values are allowed because
  their publication is before prediction time.
- The complete registry, fingerprint, missing fields, imputations and source event
  IDs are persisted with each snapshot.

## Executed evidence

```text
PYTHONPATH=apps/backend:packages/intelligence/src:simulator \
  .venv/bin/pytest apps/backend/tests/test_predictive_end_to_end.py -q
2 passed

make test-backend
38 passed

.venv/bin/pytest packages/intelligence/tests/test_feature_registry.py \
  packages/intelligence/tests/test_feature_snapshot.py \
  packages/intelligence/tests/test_forecast_baseline.py \
  packages/intelligence/tests/test_forecast_gbt.py -q
73 passed
```

## Honest limitation

The live demo currently selects `comparable_median.v1`, so only weekday,
service-window and historical demand affect its point forecast. All registered
features are safely persisted and are valid inputs to `lightgbm_gbt.v1`, but
weather, holiday and promotion must not be claimed to influence a live baseline
forecast. The GBT artifact deployment/acceptance connection remains required
before those model inputs can be called live forecast drivers.
