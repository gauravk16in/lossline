# C02 — Signal and Feature Registries

Status: complete

## Goal

Provide strict, extensible and reproducible contracts for normalized observations and model features while enforcing point-in-time forecast safety and preserving the reactive anomaly API.

## Input

- C01 architecture and artifact boundaries.
- Existing pre-reengineering C1 `NormalizedSignal` and `SignalRegistry` work.
- Leakage policy RE-006.
- Predictive prompt requirements for a generic feature registry.

## Output

- Typed normalized-signal envelope with discriminated values, quality and provenance.
- Immutable versioned signal definitions and registry.
- Immutable versioned feature definitions and registry.
- Forecast-safety enforcement using observation and ingestion time.
- Deterministic registry fingerprints.
- ADR 0003, focused tests and verification evidence.

## Files

- `packages/intelligence/src/lossline_intelligence/signals/`
- `packages/intelligence/src/lossline_intelligence/features/`
- `packages/intelligence/tests/test_normalized_signal.py`
- `packages/intelligence/tests/test_signal_registry.py`
- `packages/intelligence/tests/test_feature_registry.py`
- C02 documentation and verification.

## Contracts

`NormalizedSignal` is a strict frozen Pydantic serialization boundary. It carries schema/signal identity, outlet/entity identity, knowledge and effective time, source/category/type, a discriminated typed value, unit, dimensions, metadata, quality and provenance.

`SignalDefinition` specifies one observation type's version, category, entity, value kind, unit, forecast-safety status, staleness, leakage rationale and allowed sources.

`FeatureDefinition` specifies `feature_id`, version, source, category, data type, unit, entity grain, time semantics, availability, future-known status, transformation, missing-value strategy, staleness and leakage rationale.

Both registries are immutable, reject empty/duplicate/unknown entries, expose a registry version, and generate a deterministic SHA-256 fingerprint.

## Algorithm

Signal safety for a prediction:

1. Resolve the registered signal definition.
2. Validate category, entity, value kind, unit and source.
3. Require the definition to be forecast-safe.
4. Require `observed_at <= prediction_as_of`.
5. Require `ingested_at <= prediction_as_of`.
6. Reject records older than maximum staleness.

Feature definitions are validated when constructed. `future_known=True` is permitted only with `FUTURE_KNOWN` availability and static, forecast-vintage or scheduled-future time semantics. Forecast-vintage features must be future-known. Actual point-in-time feature selection belongs to C04.

## Assumptions

- An effective period may be in the future when the exact value/vintage was already known.
- `observed_at` is source knowledge time and provenance `ingested_at` is LOSSLine availability time.
- JSON observation values are bounded to 256 nodes and eight levels and prohibit floats; numerical metrics use `Decimal`.
- Feature IDs are namespaced strings rather than a closed enum.

## Decisions

- Reactive and normalized signals remain separate contracts.
- Observation and feature registries remain separate.
- Missing-value policy is declared, never inferred by model code.
- Registry fingerprints become feature-snapshot and artifact inputs in later chunks.
- C02 defines semantics but does not implement the C04 feature computation pipeline.

## Failure modes

- Unknown signal or feature type.
- Duplicate identifier.
- Category, entity, value-kind, unit or source mismatch.
- Naive timestamp or invalid effective interval.
- Observation or ingestion after prediction as-of.
- Stale or explicitly unsafe observation.
- Infinite decimal or unbounded/non-JSON payload.
- Incoherent future-known and time-semantics declarations.
- Mutable global registration state.

## Tests

- Valid future-effective forecast vintage.
- Naive and invalid timestamp rejection.
- Finite decimal and bounded JSON validation.
- Registry semantic mismatch, unknown and duplicate rejection.
- Future-observed and late-ingested leakage rejection.
- At-staleness boundary acceptance and above-boundary rejection.
- Explicit forecast-unsafe rejection.
- Feature semantic coherence and historical-lag behavior.
- Fingerprint repeatability and definition-order independence.
- Full reactive intelligence regression suite.

## Integration points

- C03 emits causally coherent normalized observations.
- C04 consumes both registries and persists their versions/fingerprints in feature snapshots.
- C06 artifacts retain the feature-registry fingerprint.
- C11 dossier provenance refers to source signals and feature snapshots.
- C19 maps persistence/API payloads without redefining these models.

## Definition of done

C02 is complete when contracts and registries are implemented, leakage and semantic tests pass, fingerprints are repeatable, the existing reactive API is unchanged, the full intelligence suite passes, and verification records no unresolved failure.

