# ADR 0018 — Separate Agent Acceptance Gate

Status: accepted — 2026-08-09

## Decision

Evaluate agent choice, forbidden proposals, guard behavior, explanation grounding and consistency separately from forecast metrics. A forbidden proposal fails the agent gate even if the guard blocks it; guard safety is measured independently. Gold labels exist only in evaluation case objects.

## Consequences

Forecast quality cannot hide unsafe or inconsistent decision behavior. Strict initial grounding/safety/consistency thresholds may reject a provider until evidence justifies relaxation.

## Verification

Focused tests implement accepted, adversarial H/I-style, divergence and boundary cases and confirm label fields are absent from the live dossier.
