# C15 — Structured-First Historical Retrieval

Status: complete

## Purpose

Retrieve bounded comparable periods from typed history before considering unstructured policy documents. C15 performs no raw SQL, vector search, mutable store access, or computed-artifact override.

## Method

Structured candidates must predate `prediction_as_of` and exactly match outlet and named service window. Deterministic scores add SKU, risk-type and weekday comparability; ties use recency then ID. Results are bounded by a module-level limit and preserve evidence IDs.

Document retrieval is disabled by default and runs only when both configuration enables it and a measured corpus-admission decision is true. The MVP uses deterministic token overlap over effective policy documents with a configurable relevance floor. Documents return metadata evidence and cannot replace numeric artifacts.

## Definition of done

C15 is complete when temporal/scope filtering, scoring/tie behavior, sparse history, limits, document default-off/admission gate, relevance/effective dates, invalid inputs, prohibited query surface and full regressions pass.
