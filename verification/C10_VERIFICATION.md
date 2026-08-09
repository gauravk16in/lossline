# C10 Verification

Verification date: 2026-08-09

Status: PASS

## Commands and results

```text
.venv/bin/pytest packages/intelligence/tests/test_driver_attribution.py -q -rs
11 passed, 0 skipped

.venv/bin/pytest packages/intelligence/tests/ -q -rs
428 passed, 0 skipped

.venv/bin/pytest simulator/tests/ -q -rs
12 passed, 0 skipped
```

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| Strict frozen contract | Pydantic mutation/extra-field tests | PASS |
| Registered feature references | Unknown and duplicate feature tests | PASS |
| Deterministic ranking | Absolute score and feature tie-break test | PASS |
| Direction boundaries | Increase/decrease/neutral tests | PASS |
| Method semantics | Deviation/contribution mismatch tests | PASS |
| Sparse behavior | Empty candidates return empty tuple | PASS |
| Bounded evidence | `max_drivers` test | PASS |
| Finite Decimal discipline | NaN/Infinity rejection | PASS |
| Deterministic identity | Repeat and changed-evidence tests | PASS |
| Causal-claim prohibition | Mandatory wording-limit assertion | PASS |
| Regression safety | Intelligence and simulator suites | PASS |

## Expected versus actual

Expected: traceable attribution that can support an explanation without allowing unsupported numeric or causal claims.

Actual: registered evidence is deterministically ranked and emitted through a strict contract; unsupported method/value combinations are rejected, empty input stays empty, and every result carries a non-causal wording limit.

## Known limitations

- C10 consumes contributions; it does not yet implement a model-specific SHAP explainer.
- Synthetic feature associations are not evidence of real-world causal effects.
- Persistence, API exposure, and UI presentation remain C19/C20 work.

## Handoff

C11 can include only these typed driver artifacts in the immutable forecast dossier.
