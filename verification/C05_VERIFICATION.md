# C05 Verification

Verification date: 2026-08-09

Status: PASS

## Tests executed

C04 handoff correction:

```text
.venv/bin/pytest packages/intelligence/tests/test_feature_snapshot.py -q -rs
```

Result: 37 passed, 0 skipped.

C05 focused command:

```text
.venv/bin/pytest packages/intelligence/tests/test_forecast_baseline.py -q
```

Result: 12 passed.

Intelligence regression command: `.venv/bin/pytest packages/intelligence/tests/ -q`

Result: 267 passed.

Simulator regression command: `.venv/bin/pytest simulator/tests/ -q`

Result: 12 passed.

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| Same weekday/window median | Exact-scope forecast test | PASS |
| Four-row minimum | Below/at-threshold test | PASS |
| Deterministic backoff | Scope tests | PASS |
| Explicit category identity | Catalog-mapping test | PASS |
| Censored target exclusion | Censored-history test | PASS |
| Future-history exclusion | As-of test | PASS |
| Point/lower/upper output | Median/bounds test | PASS |
| Bounds not called probability | Versioned empirical method | PASS |
| Explicit abstention | Sparse and invalid-target tests | PASS |
| Traceable evidence | Source snapshot IDs | PASS |
| MAE/RMSE/WMAPE/bias | Rolling metrics test | PASS |
| Zero-demand WMAPE | Explicit `None` test | PASS |
| C04 integration actually executed | 37 passed, no skips | PASS |
| Full intelligence compatibility | Final regression suite | 267 passed — PASS |
| Simulator compatibility | Final regression suite | 12 passed — PASS |

## Expected versus actual

Expected: an explainable benchmark that uses only uncensored history available before the forecast.

Actual: the baseline selects the narrowest sufficiently populated comparison scope, emits traceable median and empirical bounds, abstains on inadequate evidence, and supports chronological rolling metrics.

## Known limitations

- Empirical bounds use comparable-demand dispersion, not calibrated residual quantiles.
- Very broad global fallback can lose outlet/SKU specificity; scope remains visible.
- C04 currently supplies one lag feature rather than the full C04 prompt candidate set; the baseline reads historical targets directly.
- C07 owns persisted per-row evaluation, subgroup analysis and interval coverage.

## Manual checks

- Confirmed no reactive fixture baseline enters predictive history.
- Confirmed category is not inferred from identifier text.
- Confirmed no LLM/model call or process-global state.
- Confirmed all metric arithmetic returns finite `Decimal` values or explicit `None`.

## Integration result

C05 produces the benchmark and contract required by C06. It changes no backend, database, simulator runner or frontend behavior.

## Decision references

- RE-003.
- ADR 0005.
