# ADR 0017 — Grounded Explanation and Deterministic Fallback

Status: accepted — 2026-08-09

## Decision

Accept provider prose only through a strict schema and post-generation evidence, numeric and causal-claim validation. Numeric claims must equal dossier/guard facts. Any failure returns a deterministic non-numeric template and records source/model/fallback reason.

## Consequences

Provider availability cannot block the decision workflow or invent operational facts. Conservative phrase matching may reject benign prose; expanding wording requires adversarial evaluation.

## Verification

Focused fake-provider tests cover valid grounding, failures, malformed schemas, evidence escape, grounded/unsupported numbers, percentages, causal language and deterministic fallback.
