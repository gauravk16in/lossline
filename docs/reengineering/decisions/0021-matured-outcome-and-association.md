# ADR 0021 — Matured Outcomes and Non-Causal Decision Evaluation

Status: accepted — 2026-08-09

## Decision

Record actuals only after a configurable post-window maturity delay at the exact forecast grain. Keep available, censored and missing statuses explicit; score only available outcomes. Persist forecast and decision evaluations separately. Decision evaluation may report what was observed after manager action but never claim the action caused it.

## Consequences

Late/missing/censored data cannot silently improve accuracy. Risk precision/recall/F1 have honest unavailable denominators. Decision effectiveness remains association-only until a valid causal design exists.

## Verification

Domain boundary tests, persistence/API tests, migration round trip and the React build verify maturity, exclusion, conservation, metrics and wording.
