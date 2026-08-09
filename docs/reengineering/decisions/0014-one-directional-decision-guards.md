# ADR 0014 — One-Directional Decision Guards

Status: accepted — 2026-08-09

## Decision

Model proposals are never trusted directly. Deterministic code verifies scope, evidence, constraints, policy eligibility, quantities, units, timing and approval. It can only preserve or reduce operational exposure; invalid policy or grounding fails closed.

Prep quantities use portions, a configurable maximum and `ROUND_FLOOR` increments. Physical timing requires configured lead time and execution no later than window start. Approval can be added but never removed.

## Consequences

Useful proposals may be reduced or rejected, but no model output can broaden itself after validation. Policy values remain explicit caller inputs and versioned guard evidence.

## Verification

Focused tests assert scope/evidence membership, action eligibility, exact quantity restriction, zero rounding, approval monotonicity, timing, invalid-policy rejection and deterministic results.
