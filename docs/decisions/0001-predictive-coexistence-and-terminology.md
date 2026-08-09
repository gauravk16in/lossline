# ADR 0001: Predictive coexistence and signal terminology

Status: accepted — 2026-08-09

## Context

The repository already exposes `lossline_intelligence.models.Signal` as a deterministic anomaly-detector output. The predictive design also uses “signal” for generic observations. Reusing that class would combine incompatible grains and semantics, while replacing it would destabilize the working reactive demo.

## Decision

The detector model remains source-compatible and is called `ReactiveSignal` in predictive documentation. New generic observations use the explicit class name `NormalizedSignal` under `lossline_intelligence.signals`. Raw events and normalized signals remain distinct. Predictive storage and APIs are additive until a later parity decision retires or adapts the reactive path.

Forecast safety is enforced from knowledge time and ingestion time, not effective time. Future-effective records may be safe when they were genuinely known by the prediction as-of time.

## Consequences

Call sites cannot accidentally pass anomaly outputs into feature construction. Existing tests and integrations continue to work. During coexistence, two intentionally separate contracts exist and documentation must use their qualified names.

