# C03 — Seeded Causal Synthetic Data

Status: complete

## Goal

Create a deterministic synthetic restaurant world whose latent demand, inventory fulfillment and capacity outcomes are causally separated, with explicit assumptions and golden scenarios A–G.

## Input

- C01 grain/time contracts.
- C02 signal and feature semantics.
- Golden scenario requirements A–G.
- Existing simulator boundary and reactive scenario.

## Output

- Versioned causal generator.
- Frozen context, SKU outcome and window objects.
- Stable scenario catalog A–G.
- Synthetic assumptions document and ADR 0004.
- Determinism, causal-separation and scenario tests.

## Files

- `simulator/lossline_simulator/causal_world.py`
- `simulator/lossline_simulator/scenarios/predictive.py`
- `simulator/tests/test_causal_world.py`
- C03 documents and verification.

## Contracts

One `SyntheticWindow` represents one outlet and three-hour named service window. It contains typed context, per-SKU latent/fulfilled/unfulfilled/ending quantities, workload, capacity, utilization and observable outcomes. It records generator version, scenario and seed.

The generator accepts timezone-aware window time and optional inventory/capacity interventions. Interventions affect downstream outcomes only.

## Algorithm

1. Resolve versioned scenario parameters.
2. Derive a stable scenario-local random seed.
3. Calculate per-SKU latent demand from baseline, scenario multipliers and bounded exogenous variation.
4. Apply inventory to calculate fulfillment and censoring.
5. Convert latent demand to workload.
6. Compare workload with available capacity and calculate preparation outcome.
7. Return a frozen window with no side effects.

## Assumptions

All numerical and causal assumptions are documented in `SYNTHETIC_DATA_ASSUMPTIONS.md`. They are versioned test parameters, not real restaurant facts.

## Decisions

- Generate latent demand before operational constraints.
- Use local seeded randomness and stable scenario tags.
- Keep legacy reactive and predictive simulators separate during migration.
- Own scenarios A–G here; defer agent/LLM scenarios H–J.
- Defer backend observation/event adapters to C19.

## Failure modes

- Inventory or capacity influencing latent demand.
- Process-global random mutation.
- Python randomized hashes affecting replay.
- Naive timestamps.
- Negative/unknown inventory or non-positive/non-finite capacity.
- Synthetic effect sizes presented as learned facts.
- Using fulfilled sales as an uncensored target.

## Tests

- Same-seed repeatability and changed-seed sensitivity.
- Inventory intervention invariance for latent demand.
- Capacity intervention invariance for latent demand.
- Scenario A normal behavior.
- Scenario B Friday capacity warning.
- Scenario C rain/delivery overload.
- Scenario D holiday SKU demand.
- Scenario E promotion/limited-inventory stockout.
- Scenario F weak-demand surplus.
- Scenario G missing-weather degradation.
- Invalid timestamp, inventory and capacity rejection.
- Legacy simulator regression suite.

## Integration points

C04 converts synthetic windows into point-in-time dataset rows and feature snapshots. C05–C07 consume deterministic histories and golden splits. C08/C09 compare predictions against inventory/capacity state. C19 introduces normal backend ingestion/persistence adapters. C22 runs the integrated scenarios.

## Definition of done

C03 is complete when assumptions are explicit, scenario outputs repeat, inventory/capacity causal separation is proven, A–G expectations pass, legacy simulator behavior remains green, and verification contains no unresolved failure.

