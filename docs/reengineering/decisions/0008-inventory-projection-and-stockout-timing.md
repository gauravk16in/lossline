# ADR 0008: Inventory projection and stockout timing

Status: accepted — 2026-08-09

## Problem

Inventory risk must propagate forecast uncertainty without LLM arithmetic. Stockout timing should use an intrawindow demand curve, but an MVP forecast may not always supply one. C08 also initially introduced a forward forecast dataclass despite real C05/C06 contracts now existing.

## Decision

- Projection engines consume a structural `ForecastLike` contract implemented by real baseline and GBT forecasts.
- Usable supply, safety buffer, ending inventory, shortage and surplus are deterministic across lower/point/upper demand scenarios.
- A supplied cumulative demand curve must be finite, non-decreasing and end at point demand; stockout fraction is interpolated between checkpoints.
- Without a curve, use the explicitly recorded `UNIFORM_FALLBACK_V1` method.
- Projection identity includes the timing method and curve, preventing two timing assumptions from sharing an ID.

## Consequences

The preferred method satisfies the cumulative-demand requirement while retaining an honest sparse-input fallback. Downstream UI and explanations must disclose the fallback and must not present it as precise clock-time prediction.

## Verification

- Curve interpolation and invalid-curve tests.
- Uniform fallback behavior and metadata.
- Projection-ID sensitivity to timing method.
- Direct C05 and C06 forecast compatibility.
- Golden scenarios execute without skips.

