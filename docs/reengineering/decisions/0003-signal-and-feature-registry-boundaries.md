# ADR 0003: Separate signal and feature registries

Status: accepted — 2026-08-09

## Problem

Source observations and model features have related but different semantics. A normalized weather forecast records what a provider published; a rainfall feature specifies how one eligible vintage is selected and transformed for a prediction. Combining both in one registry would obscure lineage and make leakage review incomplete.

The existing reactive detector class is also named `Signal`, creating a terminology collision with generic observations.

## Options

1. Reuse the reactive `Signal` model for all observations and features.
2. Store observations and feature transformations in one generic registry.
3. Preserve reactive signals, introduce `NormalizedSignal`, and maintain distinct signal and feature registries linked by source identifiers.

## Decision

Adopt option 3.

- Existing `lossline_intelligence.models.Signal` remains the reactive anomaly output.
- Predictive observations use `lossline_intelligence.signals.NormalizedSignal`.
- `SignalRegistry` validates observation category, entity, value kind, unit, source, staleness and forecast safety.
- `FeatureRegistry` defines model feature source, grain, type, unit, time semantics, availability, future-known status, transformation, missing strategy, staleness and leakage rationale.
- Both registries expose explicit versions and deterministic fingerprints.
- Registry instances are explicit immutable inputs; there is no mutable process-global registry.

## Consequences

One normalized observation can support multiple versioned features without duplicating source data. Feature review can examine transformations independently of ingestion. Callers must retain both registry versions/fingerprints in feature snapshots and model artifacts.

## Verification

- Unknown and duplicate entries are rejected.
- Semantic mismatches and unsafe prediction-time records are rejected.
- Incoherent future-known/time-semantics combinations are rejected.
- Fingerprints are stable and independent of registration order.
- Existing reactive tests remain green.

