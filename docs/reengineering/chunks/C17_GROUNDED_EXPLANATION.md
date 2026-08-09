# C17 — Grounded Predictive Explanation

Status: complete

## Purpose

Generate bounded structured prose from a frozen dossier and guard result. The provider may phrase evidence but cannot introduce evidence, numbers or causal conclusions. Any unavailable, failed, malformed or unsupported output uses a deterministic template.

## Contract and validation

`PredictiveExplanation` is strict and frozen with headline, risk, driver, guarded-decision and uncertainty fields plus unique evidence IDs. Evidence must belong to the dossier. Numeric tokens must exactly match typed historical metrics or the final guarded quantity. Percentages are normalized before comparison. Unsupported causal phrases are rejected.

The fallback contains no calculated or copied numeric claims, explicitly distinguishes association from causation, and references only guarded evidence. Provider access is injectable and all tests fake it.

## Definition of done

C17 is complete when grounded provider output, absent/failing/malformed provider, external evidence, unsupported/allowed numbers, causal claims, deterministic fallback, no invented fallback numbers, focused tests and regressions pass.
