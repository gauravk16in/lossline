# ADR 0011 — Curated Point-in-Time Forecast Dossier

Status: accepted — 2026-08-09

## Context

Allowing an agent to inspect raw operational stores would weaken temporal safety, provenance, grounding and evaluation isolation. Later decisions require one immutable context boundary assembled from computed artifacts.

## Decision

Use a strict typed `ForecastDossier` containing artifact references, bounded curated summaries, constraints, historical performance, data quality and provenance. Require forecasts and feature snapshots, preserve prediction-time scope, and prohibit raw stores/provider payloads and evaluation-only gold/outcome fields by making them absent from the schema.

## Consequences

- Later agents receive a stable, auditable context artifact.
- Large raw inputs cannot silently enter prompts through the dossier contract.
- Actual outcomes and gold decisions remain behind evaluation boundaries.
- Persistence and historical retrieval stay separate from pure assembly.

## Verification

Focused tests verify strict/frozen serialization, mandatory references, temporal rules, identity sensitivity/repeatability, unique provenance, curated summaries, metric validation, sparse optional fields and absence of prohibited raw/evaluation fields.
