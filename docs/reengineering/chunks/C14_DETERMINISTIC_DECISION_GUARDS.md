# C14 — Deterministic Decision Guards

Status: complete

## Purpose

Apply policy and grounding checks after C13 schema validation. A guard may accept, reduce quantity/scope, require approval, reject, or abstain. It may never increase quantity, urgency, autonomy, customer impact, or financial exposure.

## Guard checks

- dossier, outlet, named window, boundaries and forecast membership;
- evidence and considered-constraint membership;
- allowed action and action-specific quantity/unit semantics;
- finite policy bounds, maximum prep quantity and downward increment rounding;
- minimum lead time and execution before window start;
- approval required by action or high action risk.

`NO_ACTION` and `ABSTAIN` are first-class. Invalid policy is fail-closed. Rejections carry no final decision. Restrictions preserve the submitted action and only reduce quantity or add approval. `GuardResult` is strict, frozen, deterministic and versioned.

## Definition of done

C14 is complete when acceptance, every mismatch/rejection, at/below/above quantity boundaries, downward rounding, approval correction, lead-time boundaries, invalid policy, no-action/abstention, repeatability, focused tests and full regressions pass.
