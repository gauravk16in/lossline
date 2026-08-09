# C08 — Inventory Projection

Status: complete

## Goal

Convert a demand forecast and current supply state into a point-in-time
`InventoryProjection` that carries safety-buffer arithmetic, replenishment,
shortage/surplus scenarios, severity tiers, a stockout-window fraction
estimate, and a deterministic identity.

## Input

- C01 `InventoryProjection` contract (architecture).
- `ForecastResult` minimal contract (forward declaration for C05–C07).
- `opening_inventory`, `replenishment_quantity`, and configurable thresholds
  from callers.

## Output

- Structural `ForecastLike` protocol plus a compatibility test stub for downstream.
- `InventoryProjection` frozen dataclass following C01 contract.
- `ShortageSeverity` StrEnum (NONE / LOW / MEDIUM / HIGH / CRITICAL).
- `project_inventory()` pure function.
- C08 tests (59 tests).
- C08 chunk specification and verification.

## Files

- `packages/intelligence/src/lossline_intelligence/forecasting/__init__.py`
- `packages/intelligence/src/lossline_intelligence/inventory/__init__.py`
- `packages/intelligence/src/lossline_intelligence/inventory/projection.py`
- `packages/intelligence/src/lossline_intelligence/inventory/engine.py`
- `packages/intelligence/tests/test_inventory_projection.py`
- C08 documentation and verification.

## Contracts

`ForecastLike` structurally describes the fields required from forecasts.
The real C05 `BaselineForecast` and C06 `GBTForecast` both satisfy it and are
covered by integration tests. `ForecastResult` remains a compatibility test
stub rather than a competing production serialization boundary.

`InventoryProjection` is a frozen dataclass carrying supply inputs (opening,
replenishment, usable supply, safety buffer, available for demand), ending
inventory scenarios (point/lower/upper), shortage (point and worst-case) and
surplus (point and worst-case), risk assessment (stockout_risk, severity tier,
surplus_risk), stockout-window fraction, and metadata (unit, rule version,
evidence IDs).

## Algorithm

```
usable_supply      = opening_inventory + replenishment_quantity
safety_buffer      = max(min_safety_buffer, ceil(opening × safety_buffer_pct))
available_for_dem  = max(0, usable_supply - safety_buffer)

ending_inventory_point = usable_supply - demand_point_int
ending_inventory_lower = usable_supply - demand_upper_int   ← worst case
ending_inventory_upper = usable_supply - demand_lower_int   ← best case

shortage_point = max(0, demand_point_int - available_for_demand)
shortage_upper = max(0, demand_upper_int - available_for_demand)
surplus_point  = max(0, available_for_demand - demand_point_int)
surplus_lower  = max(0, available_for_demand - demand_upper_int)

stockout_risk = shortage_point > 0
surplus_risk  = surplus_point > safety_buffer × surplus_risk_multiplier

stockout_window_fraction:
  → interpolate the supplied cumulative intrawindow demand curve (preferred)
  → otherwise available_for_demand / demand_point as UNIFORM_FALLBACK_V1
  → None when no stockout projected
  → Decimal("0") when available_for_demand ≤ 0
```

## Shortage severity tiers

| Tier | Condition |
|---|---|
| NONE | shortage_point == 0 |
| LOW | 0 < ratio < 0.10 |
| MEDIUM | 0.10 ≤ ratio < 0.25 |
| HIGH | 0.25 ≤ ratio < 0.50 |
| CRITICAL | ratio ≥ 0.50 or demand_point == 0 |

Where `ratio = shortage_point / demand_point`.

## Default thresholds

All thresholds are module-level constants, never hardcoded in logic:

| Constant | Value |
|---|---|
| `DEFAULT_SAFETY_BUFFER_PCT` | 0.10 |
| `DEFAULT_MIN_SAFETY_BUFFER` | 2 |
| `DEFAULT_SURPLUS_RISK_MULTIPLIER` | 2.0 |
| `RULE_VERSION` | `"inventory.v1"` |

## Assumptions

- `ForecastResult` demand values are rounded to integers before arithmetic.
- Ending inventory can be negative (means demand exceeded supply).
- Stockout timing uses a validated cumulative demand curve when supplied. The
  versioned uniform fallback is used only when no curve is available and is
  recorded on the projection.
- Surplus risk is triggered only when surplus_point exceeds the safety buffer
  by the surplus_risk_multiplier factor.
- No backend persistence, API, or frontend changes in C08.

## Decisions

- `InventoryProjection` and the compatibility `ForecastResult` stub are frozen
  dataclasses; projection engines type against the structural `ForecastLike` protocol.
- Real C05/C06 forecasts are accepted without mapping to a duplicate model.
- `ShortageSeverity` is a `StrEnum`.
- Stockout-window fraction is `None` when no stockout is projected.
- Projection ID is a deterministic SHA-256 of the supply inputs and forecast ID.

## Failure modes

- Negative opening inventory or replenishment.
- Non-finite or negative demand values on ForecastResult.
- demand_lower > demand_point or demand_upper < demand_point.
- Naive (no timezone) timestamps on ForecastResult.
- Empty string IDs on ForecastResult.

## Tests

- Normal case: sufficient inventory, no shortage, no surplus risk.
- Safety buffer: 10% of opening, minimum enforced, custom pct, reduces available supply.
- Replenishment: adds to usable supply, prevents shortage.
- Forecast scenarios: ending inventory lower/point/upper, negative lower, worst-case shortage/surplus.
- Shortage severity: all 5 tiers including boundary cases and zero demand.
- Stockout case: shortage_point, window fraction, fraction at zero supply, calculation.
- Surplus: no risk near demand, risk on large excess, custom multiplier.
- Zero demand: no shortage, all surplus, fraction None.
- Deterministic projection ID: same inputs, different opening/replenishment.
- Input validation: negative opening/replenishment, naive timestamps, demand ordering.
- Uniform and cumulative-curve stockout timing helpers, validation and method metadata.
- Real C05 baseline and C06 GBT forecast compatibility.
- Metadata: rule_version, custom rule_version, evidence_ids, outlet/sku/window carried.
- Golden scenario E (stockout) produces stockout_risk=True.
- Golden scenario A (normal weekday) produces valid projections.
- Projection ID deterministic across runs on golden scenario.

## Integration points

- C09 `CapacityProjection` follows the same architectural pattern.
- C10 driver attribution reads `InventoryProjection` evidence.
- C11 dossier carries `InventoryProjection` references.
- C12–C14 `DecisionCandidate` constraints include inventory shortage.
- C22 integrated demo runs projection via `project_inventory()`.
- C19 persists `InventoryProjection` to `inventory_projections` PostgreSQL table.

## Definition of done

C08 is complete when: all inventory projection tests pass without skips, full regression
suite passes, projection ID
is deterministic, the structural forecast contract is frozen, safety-buffer and
replenishment formulas are verified, all 5 severity tiers have boundary tests,
stockout timing is tested, golden scenarios are covered, and
verification records no unresolved failure.
