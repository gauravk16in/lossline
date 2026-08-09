# C11 — Immutable Forecast Dossier

Status: complete

## Purpose

Assemble the bounded, point-in-time context supplied to later decision tooling. The dossier contains typed references and curated summaries, never raw database rows, event streams, provider payloads, matured actual outcomes, or gold decisions.

## Contract

`ForecastDossier` is a strict frozen Pydantic serialization boundary containing:

- immutable ID/version and outlet/named-window scope;
- prediction as-of and timezone-aware target boundaries;
- forecast and feature-snapshot references;
- optional inventory, capacity, risk, driver and policy references;
- typed historical-performance metrics;
- curated similar-period and previous-decision summaries with evidence IDs;
- typed constraints, data-quality summary and provenance IDs.

Forecast and feature-snapshot references are mandatory. Every collection is an immutable tuple, artifact/provenance references are unique, `prediction_as_of <= window_start < window_end`, and all performance metrics are finite `Decimal` values.

## Identity and isolation

`build_forecast_dossier()` deterministically hashes every decision-relevant reference, summary, constraint, quality field and provenance ID. Creation time is audit metadata and does not change dossier identity. Strict typed fields make raw tables/provider payloads and evaluation-only labels unrepresentable in the live contract.

## Boundaries

C11 constructs an in-process immutable artifact. C15 owns retrieval behavior, C16 owns durable orchestration, C18 owns labelled evaluation, and C19 owns persistence and APIs. C11 performs no DB, Redis, LLM, network, decision or outcome work.

## Definition of done

C11 is complete when contract strictness, required references, time rules, Decimal metrics, tuple immutability, raw/evaluation-label exclusion, deterministic identity, sparse optional context, focused tests and full regressions pass without unresolved verification failures.
