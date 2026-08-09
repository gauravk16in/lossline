# C10 — Structured Driver Attribution

Status: complete

## Purpose

Produce ranked, typed evidence describing which registered inputs are associated with a forecast. C10 does not calculate forecasts, infer causes, generate prose, or let an LLM invent contributions.

## Contract

`DriverEvidence` is a strict frozen Pydantic serialization boundary containing driver and forecast IDs, registered feature ID, rank, direction, method, evidence ID, non-negative ranking score, optional signed contribution, rule version, and an explicit non-causal wording limit.

Supported methods:

- `DETERMINISTIC_DEVIATION`: ranks a signed deviation produced by deterministic feature logic. It cannot carry a numeric forecast contribution.
- `MODEL_CONTRIBUTION`: ranks model-owned signed contribution evidence and must carry the numeric contribution.

Direction is `INCREASE`, `DECREASE`, or `NEUTRAL`. Neutrality uses a configurable module-level epsilon. Ranking is descending absolute score with feature ID as a deterministic tie-break; output is bounded by `max_drivers`.

## Safety and provenance

- Only feature IDs from the caller's frozen registry may be emitted.
- Duplicate features, non-finite values, missing evidence IDs, and method/contribution mismatches are rejected.
- Empty candidate input produces an empty evidence tuple rather than fabricated drivers.
- Driver IDs bind forecast, feature, rank, method, evidence, score, contribution, and rule version.
- Every artifact states that it is associated evidence and must not be described as causal.

## Boundaries

C10 accepts already-computed deterministic deviations or model contributions. It does not derive causal effects, inspect raw provider payloads, calculate SHAP values, or silently treat correlation as causation. C11 assembles these artifacts into a dossier; C14/C17 enforce allowed decisions and claims; C19 persists them.

## Definition of done

C10 is complete when strict contract tests, rank/direction boundaries, method semantics, registry validation, sparse input, deterministic identity, non-causal wording, focused tests, and full regressions pass with no skips or unresolved verification failures.
