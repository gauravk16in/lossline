"""Deterministic post-action outcome classifier.

Compares the last complete pre-action 30-minute window metrics with the first
complete post-action 30-minute window metrics.

Classification rules (CONFIG_DEFAULT, from FINAL_IMPLEMENTATION_PLAN.md):
  IMPROVED         : cancellation_rate falls >= 20 %
                     AND prep_mean_seconds does not worsen > 10 %
  WORSENED         : cancellation_rate worsens >= 15 %
                     OR prep_mean_seconds worsens >= 15 %
  NO_CHANGE        : neither of the above
  INSUFFICIENT_DATA: order_count < MIN_ELIGIBLE_ORDERS in either window

What this module does NOT do
----------------------------
- It does not claim causation ("the action caused improvement").
- It does not produce a second recommendation.
- It does not access any database.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

MIN_ELIGIBLE_ORDERS: int = 10         # CONFIG_DEFAULT
IMPROVEMENT_CANCEL_THRESHOLD: float = 0.20   # 20 % relative fall
WORSENING_THRESHOLD: float = 0.15            # 15 % relative worsening
WORSENING_PREP_TOLERANCE: float = 0.10       # 10 % allowed prep worsening
OUTCOME_VERSION = "outcome_v1"


class OutcomeClassification(StrEnum):
    IMPROVED = "IMPROVED"
    WORSENED = "WORSENED"
    NO_CHANGE = "NO_CHANGE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class WindowMetrics:
    """Aggregated metrics for one 30-minute window used in outcome comparison.

    Attributes
    ----------
    cancel_rate         : Cancellation rate (e.g. 0.12 = 12 %).
    prep_mean_seconds   : Mean preparation time in seconds.
    order_count         : Total eligible orders in the window.
    """

    cancel_rate: float
    prep_mean_seconds: float
    order_count: int


@dataclass(frozen=True)
class OutcomeResult:
    """Result of the outcome classification.

    Attributes
    ----------
    classification           : IMPROVED / WORSENED / NO_CHANGE / INSUFFICIENT_DATA.
    pre_cancel_rate          : Cancellation rate before action.
    post_cancel_rate         : Cancellation rate after action.
    cancel_rate_delta        : Relative change (negative = improvement).
    pre_prep_seconds         : Mean prep time before action.
    post_prep_seconds        : Mean prep time after action.
    prep_seconds_delta       : Relative change (negative = improvement).
    reason                   : Human-readable explanation.
    rule_version             : Version of the classification rules used.
    """

    classification: OutcomeClassification
    pre_cancel_rate: float
    post_cancel_rate: float
    cancel_rate_delta: float
    pre_prep_seconds: float
    post_prep_seconds: float
    prep_seconds_delta: float
    reason: str
    rule_version: str


def classify_outcome(
    pre: WindowMetrics,
    post: WindowMetrics,
) -> OutcomeResult:
    """Classify the post-action outcome.

    Parameters
    ----------
    pre  : Metrics from the last complete window *before* the action.
    post : Metrics from the first complete window *after* the action.

    Returns
    -------
    OutcomeResult with classification and raw metric deltas.
    """
    # --- Insufficient data guard ---
    if pre.order_count < MIN_ELIGIBLE_ORDERS or post.order_count < MIN_ELIGIBLE_ORDERS:
        return OutcomeResult(
            classification=OutcomeClassification.INSUFFICIENT_DATA,
            pre_cancel_rate=pre.cancel_rate,
            post_cancel_rate=post.cancel_rate,
            cancel_rate_delta=0.0,
            pre_prep_seconds=pre.prep_mean_seconds,
            post_prep_seconds=post.prep_mean_seconds,
            prep_seconds_delta=0.0,
            reason=(
                f"Insufficient orders for comparison "
                f"(pre={pre.order_count}, post={post.order_count}, "
                f"min={MIN_ELIGIBLE_ORDERS})."
            ),
            rule_version=OUTCOME_VERSION,
        )

    # --- Compute relative deltas (positive = worsening for cancel/prep) ---
    cancel_delta = _relative_change(pre.cancel_rate, post.cancel_rate)
    prep_delta = _relative_change(pre.prep_mean_seconds, post.prep_mean_seconds)

    # --- Classify ---
    if (
        cancel_delta <= -IMPROVEMENT_CANCEL_THRESHOLD  # cancel fell >= 20 %
        and prep_delta <= WORSENING_PREP_TOLERANCE     # prep didn't worsen > 10 %
    ):
        classification = OutcomeClassification.IMPROVED
        reason = (
            f"Cancellation rate fell {abs(cancel_delta):.1%} "
            f"(from {pre.cancel_rate:.1%} to {post.cancel_rate:.1%}). "
            f"Prep time change: {prep_delta:+.1%}."
        )
    elif cancel_delta >= WORSENING_THRESHOLD or prep_delta >= WORSENING_THRESHOLD:
        classification = OutcomeClassification.WORSENED
        reason = (
            f"Primary metric(s) worsened: "
            f"cancellation {cancel_delta:+.1%}, prep time {prep_delta:+.1%}."
        )
    else:
        classification = OutcomeClassification.NO_CHANGE
        reason = (
            f"No significant change detected: "
            f"cancellation {cancel_delta:+.1%}, prep time {prep_delta:+.1%}."
        )

    return OutcomeResult(
        classification=classification,
        pre_cancel_rate=pre.cancel_rate,
        post_cancel_rate=post.cancel_rate,
        cancel_rate_delta=round(cancel_delta, 6),
        pre_prep_seconds=pre.prep_mean_seconds,
        post_prep_seconds=post.prep_mean_seconds,
        prep_seconds_delta=round(prep_delta, 6),
        reason=reason,
        rule_version=OUTCOME_VERSION,
    )


def _relative_change(before: float, after: float) -> float:
    """Relative change: (after - before) / before.

    Positive = worsening (higher rate/time), negative = improvement.
    Returns 0.0 when before == 0 to avoid division by zero.
    """
    if before == 0.0:
        return 0.0
    return (after - before) / before
