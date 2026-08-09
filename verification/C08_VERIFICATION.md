# C08 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

Focused command:

```text
.venv/bin/pytest packages/intelligence/tests/test_inventory_projection.py -v
```

Result after C07 integration completion: 67 passed, 0 skipped.

Full regression command:

```text
.venv/bin/pytest packages/intelligence/tests/ -q -rs
.venv/bin/pytest simulator/tests/ -q -rs
```

Current post-C07 integration result: 407 intelligence tests and 12 simulator tests passed, with zero skips.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| InventoryProjection implementation | `inventory/projection.py` — frozen dataclass | PASS |
| ForecastResult minimal contract | `forecasting/__init__.py` — frozen dataclass | PASS |
| Safety-buffer formula | `_compute_safety_buffer()` — max(min, ceil(opening × pct)) | PASS |
| Replenishment arithmetic | `project_inventory()` — usable = opening + replenishment | PASS |
| Lower/point/upper scenarios | `test_ending_inventory_scenarios` | PASS |
| Shortage/surplus detection | `test_shortage_point_nonzero`, `test_surplus_risk_when_large_excess` | PASS |
| All 5 severity tiers | `TestShortageSeverity` — NONE/LOW/MEDIUM/HIGH/CRITICAL | PASS |
| Severity boundary tests | `test_boundary_low_medium`, `test_boundary_medium_high`, `test_boundary_high_critical` | PASS |
| Stockout-window fraction | Uniform and cumulative interpolation tests | PASS |
| Fraction None when no stockout | `test_no_stockout_window_fraction` | PASS |
| Fraction 0 at zero supply | `test_stockout_fraction_at_zero_inventory` | PASS |
| Deterministic projection ID | `test_same_inputs_same_id`, `test_projection_id_deterministic_across_runs` | PASS |
| Rule version carried | `test_rule_version_on_projection` | PASS |
| Evidence IDs carried | `test_evidence_ids_stored` | PASS |
| Input validation | negative opening/replenishment, naive timestamps, demand ordering | PASS |
| Golden scenario E stockout detected | `test_scenario_e_stockout_detected` | PASS |
| Golden scenario A normal | `test_scenario_a_baseline_no_stockout` | PASS |
| Real C05/C06 compatibility | BaselineForecast and GBTForecast integration tests | PASS |
| Timing method provenance | CUMULATIVE_CURVE_V1 / UNIFORM_FALLBACK_V1 tests | PASS |
| Full regression clean | 407 intelligence + 12 simulator, zero skips | PASS |

## Supply arithmetic verification (manual)

```
opening=70, replenishment=0, safety_buffer_pct=10%
usable_supply    = 70
safety_buffer    = max(2, ceil(70 × 0.10)) = max(2, 7) = 7
available        = 70 - 7 = 63
demand_point=50  → ending=20, shortage=0,  surplus=13
demand_upper=65  → ending= 5, shortage_upper=2
demand_lower=40  → ending=30, surplus_lower=23
```

Test `test_ending_inventory_scenarios` confirms all three scenarios.

## Stockout-window fraction verification (manual)

```
available=36, demand_point=50
fraction = 36/50 = 0.72
```

Test `test_stockout_fraction_calculation` confirms 0.7200.

## Handoff gates

| Gate | Status |
|---|---|
| C08 inventory projection tests passing | 67/67 PASS, no skips |
| C08 verification status | PASS |
| InventoryProjection contract frozen | Frozen dataclass, all C01 fields present |
| Forecast boundary frozen | Structural `ForecastLike`; direct C05/C06 compatibility |
| Safety-buffer formula verified | `test_buffer_is_10pct_of_opening`, `test_buffer_minimum_enforced` |
| Replenishment formula verified | `test_replenishment_adds_to_supply`, `test_replenishment_prevents_shortage` |
| All severity tiers covered | 9 severity tests including all boundaries |
| Stockout-window fraction verified | 4 dedicated tests |
| Deterministic projection ID | 4 identity tests |
| Golden scenario coverage | Scenario E (stockout) and A (normal) |
| Full regression clean | 407 intelligence + 12 simulator passed, 0 failed/skipped |

## Known limitations

- `ForecastLike` is the engine boundary; `ForecastResult` remains a test compatibility stub. Real C05/C06 forecasts pass integration tests.
- Rolling replenishment projections (mid-window restocking) not modelled — C08 uses a single pre-window replenishment.
- Uniform stockout timing is an explicitly recorded fallback when no cumulative demand curve exists.
- No backend persistence, API, or frontend changes (C19 concern).

## What was NOT changed

- Zero reactive pipeline changes.
- Zero domain model duplication.
- Zero backend/API/frontend modifications.
- `pyproject.toml` version constraint unchanged.
