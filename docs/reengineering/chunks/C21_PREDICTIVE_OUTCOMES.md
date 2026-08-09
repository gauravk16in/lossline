# C21 — Matured Actual Outcomes and Evaluation

Status: complete

## Purpose

Close the predictive measurement loop with a strict actual-outcome artifact at the identical forecast grain/window, explicit maturity, missing/censored behavior, forecast error/coverage, risk classification metrics and association-only decision evaluation.

## Outcome contract

`ActualOutcome` carries forecast/outlet/SKU/named-window identity, actual/fulfilled/unfulfilled demand, ending inventory, capacity utilization, status, source IDs, maturity time and rule version. `AVAILABLE` and `CENSORED` require conserved non-negative demand (`fulfilled + unfulfilled = actual`). `MISSING` carries no demand quantities. All metrics are finite `Decimal` values.

The configurable maturity boundary is inclusive. Before it, code returns `NOT_MATURE`; at or after it, the canonical maturity time and deterministic identity are stable across rechecks. Censored and missing outcomes are persisted but excluded from forecast scoring.

## Evaluation

- available outcomes produce signed/absolute error, interval hit and observed-shortage status;
- exact forecast grain/window mismatch is rejected;
- risk pairs produce TP/FP/TN/FN, precision, recall and F1 with explicit unavailable denominators;
- decision evaluation records only temporal association and explicitly denies causal inference.

## Integration

The C21 migration adds immutable `actual_outcomes` and `predictive_evaluations`. APIs expose matured outcome and all evaluation artifacts per forecast. Predictive Today renders available actual demand or visibly labels censored/missing exclusion. C22 maps simulator events through normal `POST /events` into these contracts.

## Definition of done

C21 is complete when below/at/above maturity, available/censored/missing, conservation, finite values, exact grain, error/interval, risk metric denominators, association wording, repeatability, migration round trip, persistence/API/UI and full regressions pass.
