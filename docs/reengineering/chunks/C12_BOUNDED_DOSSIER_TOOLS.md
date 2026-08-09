# C12 — Bounded Dossier Read Tools

Status: complete

## Purpose

Expose a minimal read-only tool surface over one immutable C11 dossier. Tools cannot query raw stores, cross dossier boundaries, write state, calculate metrics, or enumerate provider payloads.

## Contract

`DossierToolbox` provides only `get_artifact_ref()` and `get_curated_summary()`. Membership is frozen at session creation. Every attempted lookup consumes a configurable read budget, including failed lookups, and appends an immutable trace entry. Exhaustion and out-of-scope lookup are distinct typed errors. Results and referenced values are frozen.

The default read budget is a module-level constant. A zero budget is valid; a negative budget is rejected. No database, Redis, network, LLM or mutation dependency exists.

## Definition of done

C12 is complete when allowlisting, cross-dossier rejection, success/failure budget accounting, exhaustion, immutable trace/results, zero-budget behavior, prohibited surface inspection, focused tests and full regressions pass.
