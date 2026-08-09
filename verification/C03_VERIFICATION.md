# C03 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

Focused causal command:

```text
.venv/bin/pytest simulator/tests/test_causal_world.py -q
```

Result: 11 passed.

Simulator regression command: `.venv/bin/pytest simulator/tests/`

Result: 12 passed.

Intelligence regression command: `.venv/bin/pytest packages/intelligence/tests/`

Result: 218 passed.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| Seeded repeatability | Same/changed-seed test | PASS |
| Explicit causal assumptions | `SYNTHETIC_DATA_ASSUMPTIONS.md` | PASS |
| Latent demand independent of inventory | Inventory intervention test | PASS |
| Latent demand independent of capacity | Capacity intervention test | PASS |
| Frozen typed outcomes | Causal-world dataclasses | PASS |
| A–G scenario catalog | Scenario tests | PASS |
| Missing weather behavior | Scenario G test | PASS |
| Invalid input rejection | Timestamp/inventory/capacity tests | PASS |
| Legacy reactive coexistence | Simulator regression suite | 12 passed — PASS |
| Intelligence compatibility | Intelligence regression suite | 218 passed — PASS |

## Expected versus actual

Expected: a causal, replayable world rather than random columns or a scripted expected answer.

Actual: latent demand is generated first and invariant under inventory/capacity intervention; fulfillment and preparation outcomes respond independently to their relevant constraints.

## Known limitations

- The MVP capacity outcome is a documented linear approximation.
- C03 creates predictive world objects, not backend events or persisted signals.
- Local-event behavior is documented but not activated by required A–G scenarios.
- Synthetic success does not establish production forecast accuracy.
- Agent, grounding and calibration scenarios H–J are deferred.

## Manual checks

- Confirmed local RNG use with no `random.seed()` global mutation.
- Confirmed stable scenario tagging avoids Python `hash()`.
- Confirmed inventory is applied after latent demand.
- Confirmed capacity affects preparation outcome rather than demand.
- Confirmed legacy `lunch_rush.py` was not replaced.

## Integration result

C03 supplies deterministic predictive inputs for C04 while preserving the existing reactive simulator. Backend runtime is unchanged.

## Decision references

- ADR 0004.
- RE-002 and RE-006.
