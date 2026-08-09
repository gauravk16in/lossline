# ADR 0013 — Strict Terminal Decision Submission

Status: accepted — 2026-08-09

## Decision

Only a schema-valid `submit_operational_decision` tool envelope may produce a predictive `DecisionCandidate`. Plain text terminates as abstention. Schema failures receive a finite repair budget; provider failures and exhaustion also abstain. The provider is injected behind a protocol so all tests use fakes.

## Consequences

- Narration cannot accidentally become an executable decision.
- Invalid output has a bounded recovery path and an auditable terminal reason.
- Schema validity is not policy safety; C14 remains mandatory.

## Verification

Focused tests cover valid submission, free-form output, wrong tools, repair success/exhaustion, provider failure, scope mismatch, strict contracts and numeric/time validation.
