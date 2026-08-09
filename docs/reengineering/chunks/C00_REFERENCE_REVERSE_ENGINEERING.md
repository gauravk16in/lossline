# C00 — Reference Reverse Engineering and Current-System Audit

Status: complete

## Goal

Establish source-backed architectural evidence before changing LOSSLine runtime behavior. Separate reusable control patterns from reference-repository assumptions that do not fit statistical restaurant forecasting.

## Input

- Public reference repository `caleb-andersen/hackerrank-orchestrate-august26`, `main/code`.
- LOSSLine `AGENTS.md`.
- `nextLossline.md`, `FINAL_IMPLEMENTATION_PLAN.md`, and `docs/architecture.md`.
- Current backend, intelligence package, simulator, frontend, tests and deployment files.
- The predictive re-engineering prompt.

## Output

- `docs/reengineering/REFERENCE_REPO_ANALYSIS.md`
- `docs/reengineering/CURRENT_SYSTEM_AUDIT.md`
- `docs/reengineering/DECISIONS.md`
- this chunk specification
- `verification/C00_VERIFICATION.md`

## Files

Documentation and verification files only. C00 changes no executable source, configuration, migration, dependency, test, or deployment file.

## Contracts

- Capability classifications use `REAL`, `SYNTHETIC BUT COMPUTED`, `HARDCODED`, `PLACEHOLDER`, `UNUSED/ABSENT`, or `BROKEN`.
- Reference claims identify inspected source modules.
- Reusable patterns state a LOSSLine adaptation.
- Rejected patterns state why they do not fit.
- Unapproved architectural choices remain `PROPOSED` in the decision ledger.
- Facts, predictions, agent judgment, guards, and outcomes remain separate concepts.

## Algorithm

1. Inspect the reference source tree and execution documentation.
2. Trace ingestion, deterministic context, dossier, agent loop, tools, submission, guards, traces and evaluation.
3. Compare each pattern with LOSSLine's forecasting and operational-decision requirements.
4. Trace LOSSLine's executable ingestion-to-UI paths.
5. Classify capabilities from source behavior rather than planning claims.
6. Record reusable assets, misleading boundaries and migration constraints.
7. Seed the decision ledger without silently accepting proposed choices.
8. Verify that only documentation artifacts changed.

## Assumptions

- The inspected public `main` branch is the intended reference version as of the analysis date.
- Existing uncommitted C0/C1 changes belong to the user and are preserved.
- `FINAL_IMPLEMENTATION_PLAN.md` continues to govern the reactive implementation until the proposed predictive authority change is accepted.

## Decisions

- Reference patterns are adapted selectively; the LLM does not own numerical demand prediction.
- The current React application is identified as the canonical frontend based on executable deployment and architecture evidence, but its cleanup remains proposed.
- Predictive chunk numbering and all downstream formulas remain proposed pending approval.

## Failure modes

- Mistaking documentation for executable behavior.
- Copying competition-specific model ownership into demand forecasting.
- Treating fixture or mock values as computed intelligence.
- Marking proposed architecture as accepted.
- Modifying runtime code during a read-only analysis gate.
- Failing to preserve the working reactive path.

## Tests

- Confirm every required C00 artifact exists and is non-empty.
- Confirm the reference pattern table contains the five required columns.
- Confirm all required audit capability areas are classified.
- Confirm the decision ledger contains every minimum decision topic.
- Confirm no executable file was modified by C00.
- Run Markdown-oriented manual checks for source names, status language and broken links where feasible.

## Integration points

- C01 consumes the target-boundary and terminology findings.
- C02 consumes the leakage and registry findings.
- C11 consumes the dossier pattern.
- C12–C14 consume the bounded-tool, strict-submission and guard patterns.
- C18 consumes label isolation, calibration and consistency patterns.
- C19–C22 consume the current-system migration audit.

## Definition of done

C00 is complete when the five documentation artifacts exist, reference and current-system claims are source-backed, required patterns and capabilities are covered, proposed decisions are visibly unapproved, no runtime files changed, and the verification report passes.

