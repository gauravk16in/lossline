# C16 — Durable Predictive Orchestration

Status: complete

## Purpose

Add a meaningful predictive LangGraph workflow whose nodes perform real artifact operations: load a frozen dossier, invoke the bounded C13 submission loop, run C14 guards, and persist a manager-review checkpoint. This is additive; the reactive investigation graph remains operational during coexistence.

## Workflow

```text
load_dossier → submit_decision → guard_decision
  → rejected/abstained: finish
  → accepted/restricted: durable manager_review_checkpoint
  → explicit APPROVE/REJECT resume
```

`SqliteReviewCheckpointStore` persists versioned state by thread ID. A newly constructed store/process can reopen and resume review. Re-running an existing thread is idempotent and does not call the provider again. A thread cannot be rebound to another dossier. Manager completion is idempotent for the same choice and rejects conflicting replay.

## Boundaries

- The graph computes no metrics, forecast, projection, attribution, quantity or policy value.
- Only guarded decisions reach manager review; guard rejection and agent abstention are terminal.
- C16 authorizes no execution and exposes no HTTP API.
- C19 migrates the checkpoint adapter to normal backend persistence as needed while retaining semantics.

## Definition of done

C16 is complete when real node effects, durable reopen/resume, guard restriction, terminal abstention, rerun idempotency, thread isolation, manager replay/conflict behavior, reactive graph compatibility, focused tests and regressions pass.
