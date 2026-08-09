# ADR 0009 — Workload Minutes and Effective Capacity

Status: accepted — 2026-08-09

## Context

Demand quantity cannot be compared directly with kitchen supply. SKU mix changes operational load, available station time is not fully productive, and an LLM must not invent capacity arithmetic.

## Decision

C09 converts each SKU forecast scenario to workload minutes using configured workload minutes per unit, sums them into a shared outlet pool, and compares them with available station-minutes multiplied by a configurable efficiency factor. Point utilization determines deterministic risk tiers and congestion; lower and upper utilization preserve forecast uncertainty. Physical overload means utilization of at least one.

The MVP deliberately uses one shared outlet capacity pool. It does not represent station routing, batching, queue dynamics, or skill-specific staffing. Those omissions remain explicit evidence limitations rather than simulated precision.

## Consequences

- Capacity and inventory risks remain distinct.
- All arithmetic is finite `Decimal`, versioned, deterministic, and repeatable.
- Risk thresholds and operating values are module defaults that callers may override.
- The projection ID changes whenever any decision-relevant input changes.
- Later explanations may say the workload exceeds configured effective capacity; they may not claim a specific station caused the overload without new evidence.

## Verification

`packages/intelligence/tests/test_capacity_projection.py` verifies workload conservation, thresholds, uncertainty ordering, overload, validation, deterministic identity, synthetic scenarios, and absence of inventory fields. Full intelligence and simulator regressions must remain clean.
