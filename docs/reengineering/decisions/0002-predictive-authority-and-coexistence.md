# ADR 0002: Predictive authority and reactive coexistence

Status: accepted — 2026-08-09

## Problem

`FINAL_IMPLEMENTATION_PLAN.md` governs the working reactive lunch-rush demo, `nextLossline.md` proposes a predictive C0–C18 migration, and the approved re-engineering sequence introduces a more explicit C00–C22 program. Treating all three as one authority would create conflicting chunk IDs and allow predictive changes to destabilize the reactive product.

## Options

1. Replace the reactive architecture immediately.
2. Keep `nextLossline.md` C0–C18 as the only predictive sequence.
3. Adopt C00–C22 for predictive work while retaining the existing authority for the reactive path during migration.

## Decision

Adopt option 3.

- `docs/reengineering/` and C00–C22 govern predictive re-engineering.
- `FINAL_IMPLEMENTATION_PLAN.md` continues to govern the existing reactive path until an explicit retirement decision.
- `nextLossline.md` remains source analysis and is mapped into the new sequence; it is not an independent implementation queue.
- Existing uncommitted C0 architecture work maps to C01.
- Existing uncommitted C1 signal work maps to C02 and must pass C02 reconciliation.
- Predictive storage and APIs are additive until parity and migration gates pass.

## Consequences

The working incident demo remains available while predictive capabilities mature. Documentation must qualify whether a contract belongs to the reactive or predictive path. Some existing chunk documents require mapping notices, but their evidence is preserved.

## Verification

- No chunk has two owners.
- C01 documents the cross-path boundaries.
- C02 verifies the existing signal implementation against the new registry requirements.
- Integration chunks prove coexistence before any reactive retirement.

