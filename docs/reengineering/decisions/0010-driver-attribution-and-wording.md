# ADR 0010 — Driver Attribution and Wording Limits

Status: accepted — 2026-08-09

## Context

Operational users need evidence for forecast movement, but promotion, weather, calendar and outlet factors may be confounded. A ranked feature or model contribution is not proof of causality.

## Decision

Represent forecast drivers as structured `DriverEvidence`. Permit deterministic deviation ranking without a numeric forecast contribution and model-owned contribution ranking only when a signed numeric contribution is supplied. Rank by absolute score with deterministic tie-breaking, require registered feature and evidence references, and attach a mandatory non-causal wording limit to every result.

## Consequences

- Empty or invalid evidence cannot become an explanation.
- An LLM may summarize these artifacts but cannot compute, change, or causalize them.
- The initial implementation is method-agnostic and does not claim SHAP support.
- Later model-specific explainers can be added only as a new version with evaluation evidence.

## Verification

Focused tests cover strict/frozen serialization, method semantics, sign/direction, neutrality, deterministic ranking and identity, bounded output, sparse input, non-finite rejection, registry membership, duplicates, and non-causal wording.
