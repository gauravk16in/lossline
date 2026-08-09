# ADR 0015 — Structured Retrieval Before Documents

Status: accepted — 2026-08-09

## Decision

Comparable operational history is retrieved from typed records using point-in-time, outlet, service-window, SKU, risk and weekday semantics. Unstructured document retrieval remains default-off and requires both explicit enablement and prior corpus admission based on measured benefit. No vector database is introduced.

## Consequences

Numeric history stays auditable and cannot be overwritten by text. The initial token-overlap document method is intentionally modest and must be versioned/re-evaluated before replacement.

## Verification

Focused tests cover future leakage, scope, deterministic ranking, sparse results, limits, document gating, relevance, effective dates and absence of raw/vector surfaces.
