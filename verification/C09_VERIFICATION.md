# C09 Verification

Verification date: 2026-08-09

Status: PASS

## Commands and results

```text
.venv/bin/pytest packages/intelligence/tests/test_capacity_projection.py -q -rs
57 passed, 0 skipped

.venv/bin/pytest packages/intelligence/tests/ -q -rs
417 passed, 0 skipped

.venv/bin/pytest simulator/tests/ -q -rs
12 passed, 0 skipped
```

## Requirement matrix

| Requirement | Evidence | Result |
|---|---|---|
| Frozen capacity contract | `CapacityProjection` frozen dataclass | PASS |
| Workload conservation | Single- and multi-SKU scenario tests | PASS |
| Effective capacity | Efficiency boundary and custom-factor tests | PASS |
| Lower/point/upper utilization | Ordered scenario and exact arithmetic tests | PASS |
| Tier boundaries | Below/at/above defaults plus custom thresholds | PASS |
| Physical overload | Sufficient/insufficient capacity tests | PASS |
| Congestion/preparation formula | Exact and custom-base tests | PASS |
| Deterministic identity | Repeatability and changed-input tests | PASS |
| Invalid/sparse inputs | Empty, non-finite, negative, inverted, naive and duplicate tests | PASS |
| Inventory separation | Type and field-boundary tests | PASS |
| Golden scenarios | C03 scenarios A and B execute without skips | PASS |
| Regression safety | Intelligence and simulator suites | PASS |

## Expected versus actual

Expected: deterministic outlet-level workload and capacity evidence that preserves forecast scenarios and abstains through validation rather than fabricating arithmetic.

Actual: C09 computes shared-outlet workload, effective capacity, utilization, congestion, preparation time, overload and risk tier from validated inputs. Identity covers every decision-relevant input, and all synthetic integrations execute.

## Known limitations

- The MVP aggregates stations into a shared capacity pool.
- It does not model station routing, batching, nonlinear queues, breaks, or skill-specific staffing.
- Synthetic scenarios validate engineering behavior, not real outlet calibration.
- Persistence, APIs, and UI integration belong to C19/C20.

## Handoff

C10 may consume C09 projections as deterministic driver evidence. No reactive runtime behavior changed.
