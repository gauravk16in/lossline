# ADR 0016 — Durable Predictive Review Checkpoint

Status: accepted — 2026-08-09

## Decision

Use a separate predictive LangGraph with real decision/guard nodes and a SQLite-backed versioned checkpoint at manager review. Persist after every stage, stop after a guarded candidate, and require explicit approve/reject resume. Existing thread execution and finalized manager decisions are idempotent; conflicting replay fails.

## Consequences

The predictive path can survive process restart without repeating provider calls. SQLite is the one-machine implementation; C19 may adapt storage to PostgreSQL without changing lifecycle semantics. The existing reactive graph is not removed in C16.

## Verification

Backend tests reopen the store, resume review, assert quantity restriction, provider-call idempotency, abstention terminal behavior, dossier/thread isolation and manager conflict rejection. Existing reactive graph tests also pass.
