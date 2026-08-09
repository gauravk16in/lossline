# C07 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

Environment remediation:

- Installed pinned package dependencies into `.venv`.
- Installed macOS `libomp`, required by LightGBM.
- Added explicit `scipy==1.18.0` dependency pin.

Focused C06+C07 command:

```text
.venv/bin/pytest packages/intelligence/tests/test_forecast_gbt.py packages/intelligence/tests/test_forecast_evaluation.py -q
```

Result: 25 passed.

Combined C06–C08 focused command:

```text
.venv/bin/pytest packages/intelligence/tests/test_forecast_gbt.py packages/intelligence/tests/test_forecast_evaluation.py packages/intelligence/tests/test_inventory_projection.py -q -rs
```

Result: 92 passed, 0 skipped.

Full intelligence command: `.venv/bin/pytest packages/intelligence/tests/ -q -rs`

Result: 407 passed, 0 skipped.

Simulator command: `.venv/bin/pytest simulator/tests/ -q`

Result: 12 passed.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| Per-row forecast records | `ForecastEvaluationRow` | PASS |
| Chronological expanding windows | Rolling evaluator and cutoff test | PASS |
| Concurrent-window leakage prevention | Unmatured-row exclusion regression test | PASS |
| MAE/RMSE/WMAPE/bias | Exact metric test | PASS |
| Interval coverage and width | Exact metric test | PASS |
| Baseline versus model | Paired rows and summaries | PASS |
| Outlet/SKU/window/band subgroups | Subgroup dimension test | PASS |
| Five-percent improvement gate | Acceptance boundary test | PASS |
| Ten-percent subgroup limit | Subgroup rejection test | PASS |
| Configurable subgroup limit | Custom threshold test | PASS |
| Paired comparison evidence | Mismatched count rejection test | PASS |
| Censored outcomes not scored | Censored rolling test | PASS |
| Zero-demand behavior | WMAPE unavailable test | PASS |
| Deterministic report | Repeated rolling report test | PASS |
| C06 residual sign | Correct inversion in `gbt.py` | PASS |
| Python 3.12 LightGBM execution | Local focused run | PASS |
| Full intelligence compatibility | Final regression | 407 passed — PASS |
| Simulator compatibility | Final regression | 12 passed — PASS |

## Expected versus actual

Expected: formal future-window evaluation capable of rejecting a trained but operationally unacceptable model.

Actual: every origin retrains on prior rows, emits paired baseline/model evidence, aggregates required diagnostics and produces an explicit acceptance outcome with subgroup safeguards.

## Known limitations

- C06 still uses an internal holdout when training at each origin; C07 remains leakage-safe but does more computation than a production refit policy may require.
- String/categorical encoding remains absent from C06.
- Synthetic rows are sufficient for engineering verification, not real-world model acceptance.
- Risk precision/recall/F1 requires C08/C09 outcomes and is completed in C21.

## Integration result

C07 produces the gate C19 must consult before loading the GBT. C08 compatibility is verified next; no backend or frontend behavior changed.

## Decision references

- RE-005 and RE-007.
- ADR 0007.
