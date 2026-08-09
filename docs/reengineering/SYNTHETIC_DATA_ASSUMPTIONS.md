# Synthetic Data Assumptions

Status: accepted for C03

Generator version: `causal_world.v1`

## Purpose

The synthetic world supplies deterministic, inspectable data for engineering and evaluation when production restaurant history is unavailable. It is not evidence that the same effect sizes hold in a real restaurant. Model acceptance on synthetic data means the pipeline can recover documented structure; it does not establish production accuracy.

## Causal ordering

For every outlet × SKU × service window:

```text
base latent demand
  × calendar/service effect
  × weather/context effect
  × promotion/holiday/event effect
  × small seeded exogenous variation
  = latent demand

latent demand + inventory
  → fulfilled and unfulfilled quantities

latent demand × SKU workload + available capacity
  → utilization and preparation outcome
```

Inventory and capacity are applied only after latent demand is generated. Changing inventory may change fulfillment and stockout but cannot change latent demand. Changing capacity may change overload and preparation time but cannot change latent demand.

## Catalog and units

| SKU | Base dinner demand | Standard workload | Normal opening inventory |
|---|---:|---:|---:|
| Chicken Biryani | 52 portions | 8 minutes/portion | 70 portions |
| Mutton Biryani | 28 portions | 10 minutes/portion | 40 portions |
| Aloo Biryani | 20 portions | 6 minutes/portion | 30 portions |

Quantities use whole portions. Workload and capacity use minutes. The initial window is three hours. Values are CONFIG_DEFAULT synthetic parameters, not operational facts.

## Context effects

- Normal weekday dinner multiplier: `1.00`.
- Friday dinner multiplier: `1.25`, with reduced available capacity to create a capacity-warning case.
- Rain multiplier: `1.12`; delivery share rises from `0.40` to `0.68`.
- Holiday multiplier: `1.30`; extra capacity and inventory isolate high demand from forced stockout.
- Targeted promotion multiplier: `1.35` for the promoted SKU only.
- Weak-demand multiplier: `0.62`; opening inventory doubles.
- A configured nearby local event would multiply demand by `1.10`; C03's required A–G catalog does not activate this factor, so it cannot be used as golden evidence yet.
- Missing weather applies no hidden weather effect and lowers data quality to `0.75`.
- Seeded exogenous variation is uniform within ±2.5% per SKU/window.

Effects are multiplicative when combined. Quantities are rounded half-up only after all demand effects are applied.

## Capacity behavior

```text
workload_minutes = Σ(latent_demand × sku_workload_minutes)
utilization = workload_minutes / available_capacity_minutes
overloaded = workload_minutes > available_capacity_minutes
mean_preparation_minutes = 15 × max(1, utilization)
```

This first generator uses a linear workload approximation. It does not claim to model station bottlenecks, batching or queue dynamics; C09 owns the production capacity model.

## Inventory behavior

```text
fulfilled = min(latent_demand, opening_inventory)
unfulfilled = latent_demand - fulfilled
ending_inventory = opening_inventory - fulfilled
stockout = unfulfilled > 0
```

The promotion scenario limits Chicken Biryani opening inventory to 45 portions. This demonstrates censoring: fulfilled sales must not be treated as latent demand.

## Golden scenarios owned by C03

| ID | Scenario | Expected world property |
|---|---|---|
| A | Normal weekday | No stockout and no overload |
| B | Friday dinner surge | Higher demand and overload |
| C | Rain/delivery surge | Higher delivery share/demand and overload |
| D | Holiday surge | Higher SKU demand without a forced stockout |
| E | Promotion plus limited inventory | Targeted SKU stockout |
| F | Weak demand plus high inventory | Ending surplus and no overload |
| G | Missing weather | Demand still generated with reduced data quality |

Scenarios H–J concern guard rejection, explanation grounding and calibration failure. They belong to C14, C17 and C18 rather than the causal demand generator.

## Reproducibility

- Callers supply an integer seed and timezone-aware window start.
- The generator uses a local `random.Random`; it never mutates process-global random state.
- Scenario seeds derive from stable scenario strings, not Python's randomized `hash()`.
- Identical generator version, scenario, seed and overrides produce equal frozen outputs.
- Changing seed changes exogenous variation but not causal structure.

## Limitations and prohibited claims

- Effect sizes are synthetic assumptions, not learned causal estimates.
- Scenario correctness does not prove forecast generalization.
- Promotion, rain, holiday and event effects must not be described as causal in production without suitable evidence.
- The generator does not yet emit predictive observations through backend APIs; C19 owns persistence/ingestion adapters.
- The legacy lunch-rush event script remains available for reactive coexistence and is not treated as a forecasting dataset.

