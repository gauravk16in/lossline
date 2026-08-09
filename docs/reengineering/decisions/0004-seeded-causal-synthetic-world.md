# ADR 0004: Seeded causal synthetic world

Status: accepted — 2026-08-09

## Problem

LOSSLine needs predictive development data before production restaurant history is available. The existing simulator scripts symptoms and recovery to trigger one reactive incident. Training or evaluating a predictor on that trace would reward hardcoded expectations and conflate sales, inventory and demand.

## Options

1. Generate independent random feature and target columns.
2. Reuse the scripted lunch-rush incident as forecasting data.
3. Generate latent demand first from explicit context assumptions, then separately apply inventory and capacity.

## Decision

Adopt option 3 with deterministic seeds and versioned parameters. Preserve the legacy scenario for reactive coexistence. C03 produces frozen window outcomes and scenarios A–G; downstream adapters later translate them to normalized observations and normal ingestion APIs.

## Consequences

Leakage and censoring can be tested directly. Scenario effects are intentionally inspectable, but synthetic evaluation cannot establish real-world model accuracy. Generator-version changes invalidate dependent dataset fingerprints and require renewed verification.

## Verification

- Same inputs repeat exactly; changed seeds alter variation.
- Inventory and capacity overrides do not alter latent demand.
- Scenario A–G properties pass.
- Naive timestamps, invalid capacity and invalid inventory fail.
- Legacy simulator tests remain green.

