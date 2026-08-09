# C1 — Normalized Signal Contract and Registry

Status: complete

> Mapping notice: this pre-reengineering C1 artifact is preserved as implementation history. Its responsibility is now owned and extended by `docs/reengineering/chunks/C02_SIGNAL_REGISTRY.md` under ADR 0003. C02 adds the required feature registry and reproducibility fingerprints.

## Scope

C1 adds the predictive observation boundary without altering the reactive detector contract.

## Contract

`lossline_intelligence.signals.NormalizedSignal` contains:

- schema and signal identity;
- canonical `outlet_id`, typed entity identity, category, and namespaced signal type;
- `observed_at` knowledge time and half-open effective period;
- a discriminated decimal, integer, boolean, categorical, timestamp, or bounded-JSON value;
- unit, dimensions, metadata, source quality, and provenance;
- strict extra-field rejection, timezone normalization, finite decimals, unique quality issues, and valid temporal ordering.

`SignalDefinition` freezes one signal type's version, category, entity, value kind, unit, allowed sources, staleness, forecast-safe status, and leakage rationale. `SignalRegistry` rejects unknown types, duplicate registrations, and semantic mismatches.

## Forecast-safety rule

For prediction time `prediction_as_of`, a usable signal must:

1. match its registry definition;
2. be marked forecast-safe;
3. have `observed_at <= prediction_as_of`;
4. have provenance `ingested_at <= prediction_as_of`; and
5. be no older than the definition's maximum staleness.

Effective time is deliberately not constrained to the past. A promotion or weather forecast for a future service window is safe when its exact vintage was already known. Actual weather and realized outcomes must be registered as not forecast-safe.

## Boundaries and non-goals

- C1 defines pure package contracts; persistence and ingestion adapters belong to C15.
- C1 does not freeze the C3 feature registry. Signal definitions and feature definitions are distinct.
- Registry instances are explicit inputs. No mutable process-global registry is introduced.
- The existing detector `models.Signal` remains unchanged.

## Definition of done

- Typed envelope and quality/provenance contracts validate at serialization boundaries.
- Registry validates type, category, entity, unit, and source.
- Point-in-time tests prove future-observed and late-ingested records are excluded.
- At-boundary, stale, unsafe, unknown, malformed, and repeatability cases pass.
- The full pre-existing intelligence test suite remains green.
