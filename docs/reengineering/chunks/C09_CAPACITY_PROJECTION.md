# C09 — Capacity Projection

Status: complete

## Purpose

Convert outlet × SKU demand forecast scenarios into deterministic shared-outlet workload, effective capacity, utilization, congestion, preparation-time, overload, and risk-tier evidence. C09 keeps capacity risk separate from C08 inventory risk and performs no LLM arithmetic.

## Inputs

- One or more SKU tuples containing lower/point/upper forecast demand and workload minutes per unit.
- Outlet, named service window, timezone-aware boundaries, and forecast identity.
- Available station-minutes, efficiency factor, base preparation minutes, risk thresholds, rule version, and evidence IDs.

## Outputs

- Frozen `CapacityProjection` domain object.
- `CapacityRiskTier`: `SAFE`, `MODERATE`, `HIGH`, or `CRITICAL`.
- Pure `project_capacity()` engine with deterministic `cap_` identity.

## Frozen formulas

```text
workload_scenario = Σ(demand_scenario_sku × workload_minutes_per_unit_sku)
effective_capacity = available_capacity_minutes × efficiency_factor
utilization_scenario = workload_scenario / effective_capacity
congestion_factor = max(1, utilization_point)
mean_preparation_minutes = base_preparation_minutes × congestion_factor
overloaded = utilization_point >= 1
```

All results use finite `Decimal` inputs and four decimal places with `ROUND_HALF_UP`. Default utilization tier boundaries are 0.70, 0.90, and 1.00 and remain caller-overridable module constants. Overload remains the physical `utilization >= 1` condition even when display/risk thresholds are overridden.

## Validation and identity

- IDs and service-window names are non-empty.
- Windows are timezone-aware and strictly increasing.
- Capacity, workload and preparation inputs are finite; supply and per-unit workload are positive.
- Demand satisfies `0 <= lower <= point <= upper` for every SKU.
- Efficiency is in `(0, 1]`; risk thresholds are finite and strictly increasing.
- Evidence IDs are non-empty and unique.
- Projection identity binds forecast/scope/window, all workload rows, capacity, preparation, efficiency, thresholds, rule version, and evidence IDs.

## Boundaries

- C09 aggregates SKU workload into one shared outlet capacity pool. Station-specific routing, batching, and queue simulation are intentionally outside this MVP formula and must not be claimed.
- C09 does not persist data or change backend, simulator ingestion, reactive intelligence, or frontend behavior.
- C10 may read the projection as driver evidence; C11 carries its reference in the immutable dossier; C19 adds persistence/runtime adapters.

## Verification

Focused tests cover below/at/above every tier, overload, lower/point/upper conservation, sparse/invalid inputs, custom thresholds, deterministic identity, repeatability, inventory separation, and synthetic scenarios A and B without skips.

## Definition of done

C09 is complete when its focused suite passes without skips, all intelligence and simulator regressions pass, RE-009 is accepted with an ADR, formulas and limitations are documented, and `verification/C09_VERIFICATION.md` records no unresolved failure.
