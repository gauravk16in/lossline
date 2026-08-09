# ADR 0012 — Bounded Read Tools

Status: accepted — 2026-08-09

## Decision

Decision support receives exactly two read-only operations scoped to artifact references and curated summaries already admitted to one frozen dossier. Every attempt consumes a finite per-session budget and is traced. Raw queries and writes are absent from the interface.

## Consequences

The agent cannot expand its own evidence scope or hide repeated failed lookups. Persistence adapters added later may resolve references, but must preserve membership, budget and trace semantics.

## Verification

`test_dossier_tools.py` covers scope, budget, failure accounting, immutability, trace repeatability and absence of raw/write methods.
