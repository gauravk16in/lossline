# C01 — Architecture and Contracts

Status: complete

## Goal

Freeze the predictive product boundary, canonical grain and time semantics, artifact responsibilities, ownership, agent/guard/evaluation separation, and incremental coexistence path before numerical implementation begins.

## Input

- C00 reference analysis and current-system audit.
- Predictive re-engineering prompt.
- `AGENTS.md`, `nextLossline.md`, `FINAL_IMPLEMENTATION_PLAN.md` and `docs/architecture.md`.
- Existing C0/C1 working-tree artifacts.

## Output

- `docs/reengineering/ARCHITECTURE_AND_CONTRACTS.md`
- ADR 0002.
- Updated decision ledger statuses.
- Mapping notice in the earlier `docs/CHUNK_C0.md`.
- This chunk specification and `verification/C01_VERIFICATION.md`.

## Files

Documentation only. Typed implementations are owned by C02 and later chunks.

## Contracts

- Canonical predictive grain: outlet × SKU × named service window.
- UTC persisted timestamps and explicit prediction as-of semantics.
- Latent demand is separate from sales and fulfillment.
- Facts, predictions, judgment, guards and outcomes are separate artifacts.
- Core artifact responsibilities and references are frozen.
- PostgreSQL is durable truth; Redis is transport only.
- `packages/intelligence/` owns deterministic domain logic.
- One bounded decision agent receives a curated dossier.
- Guards are deterministic and one-directional.
- React is the canonical frontend.
- Reactive behavior remains source-compatible during migration.

## Algorithm

1. Reconcile the C00 findings with existing architecture documents.
2. Freeze product vocabulary, grain, time and ownership.
3. Define minimum responsibilities for every cross-chunk artifact.
4. Freeze LLM, agent, tool, guard, retrieval and evaluation boundaries.
5. Assign unresolved formulas and thresholds to their owning chunks.
6. Record the authority/coexistence decision.
7. Verify documentation completeness without changing runtime behavior.

## Assumptions

- Named service windows best match manager planning; exact window schedules remain configuration.
- The initial demo remains Asia/Kolkata but contracts are multi-outlet.
- Later chunks may extend fields through versioned contracts without weakening C01 invariants.

## Decisions

- C00–C22 is the predictive implementation sequence.
- The reactive plan retains authority over the existing system during coexistence.
- React is canonical; backend HTML retirement is gated in C20.
- Numerical forecasting remains outside the LLM and LangGraph formulas.
- One bounded decision agent is the default.
- Structured retrieval precedes optional document retrieval.

## Failure modes

- Reusing `Signal` for incompatible reactive and predictive semantics.
- Confusing fulfilled sales with latent demand.
- Allowing effective time to replace knowledge time.
- Duplicating intelligence formulas in backend orchestration or frontend code.
- Allowing agent prose to become a decision without submission and guards.
- Treating improvement after action as causal proof.
- Freezing later numerical policy without evidence from its owning chunk.

## Tests

- Required architecture sections and artifacts exist.
- Every core artifact has an owner and minimum responsibility.
- Required separation principles are explicit.
- Deferred decisions have named owning chunks.
- Authority and coexistence have an accepted ADR.
- No executable source changes are part of C01.
- Existing intelligence suite remains green as a compatibility check.

## Integration points

C02 implements normalized observations and registry compatibility. C03–C11 produce the facts, predictions, projections, risks, drivers and dossier. C12–C18 implement bounded judgment, guards, retrieval, orchestration, explanation and agent evaluation. C19–C22 integrate persistence, React, outcomes and the demo.

## Definition of done

C01 is complete when architecture and contracts are documented, authority/coexistence is accepted, later decisions have owners, the reactive path is unchanged, existing tests pass, and verification records the evidence.

