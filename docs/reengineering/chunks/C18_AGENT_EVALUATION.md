# C18 — Label-Isolated Agent Evaluation

Status: complete

## Purpose

Evaluate operational decision selection, forbidden actions, guard safety, explanation grounding and equivalent-case consistency independently from forecast accuracy. Gold labels live only in evaluation contracts and never enter C11 dossiers or live feature construction.

## Metrics and gate

- acceptable final-action rate;
- forbidden submitted-action rate;
- required-evidence plus explanation-grounding rate;
- unsafe-proposal guard-block rate;
- final-action consistency across equivalence groups.

Default acceptance requires at least 0.80 acceptable actions, zero forbidden submissions, and 1.00 grounding, guard safety and consistency. All thresholds are finite configurable module constants. Reports are frozen, deterministic and provide explicit rejection reasons. Cases and observations must pair one-to-one.

## Definition of done

C18 is complete when accepted gold cases, forbidden-but-blocked and unsafe-accepted cases, missing evidence/grounding, equivalent-case divergence, at/below/above acceptance boundary, pairing validation, label isolation, repeatability and regressions pass.
