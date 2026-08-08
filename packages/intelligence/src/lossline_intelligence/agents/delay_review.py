"""Deterministic delay-review-spike detector.

Responsibility
--------------
Given a list of reviews in the current window, decide whether there is a
significant cluster of low-rated reviews containing delay-related language.

Trigger condition:
  At least 2 reviews with rating <= 2 that contain at least one delay keyword.

Severity brackets (qualifying review count):
  2 – 3  → LOW
  4 – 5  → MEDIUM
  6 – 7  → HIGH
  8 +    → CRITICAL

What this module does NOT do
----------------------------
- It does not perform sentiment analysis.
- It does not call an LLM.
- It does not infer why delays occurred.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from lossline_intelligence.models.signal import (
    SEVERITY_SCORE,
    Severity,
    Signal,
    SignalType,
)

MIN_QUALIFYING_REVIEWS = 2
MAX_QUALIFYING_RATING = 2  # ratings <= this value are "negative"
DETECTOR_VERSION = "delay_review_spike.v1"

# Default delay keyword set.  Keyword matching is case-insensitive and
# uses substring search — no NLP, no ML.
DEFAULT_DELAY_KEYWORDS: frozenset[str] = frozenset(
    {
        "late",
        "delay",
        "delayed",
        "slow",
        "wait",
        "waiting",
        "long time",
        "took forever",
        "never arrived",
        "cold",
    }
)

_SEVERITY_BRACKETS: list[tuple[int, Severity]] = [
    (8, Severity.CRITICAL),
    (6, Severity.HIGH),
    (4, Severity.MEDIUM),
    (2, Severity.LOW),
]


@dataclass(frozen=True)
class ReviewObservation:
    """A single customer review within the observation window.

    Attributes
    ----------
    event_id : Source event identifier.
    rating   : Integer rating (e.g. 1–5).
    text     : Review body text (may be empty).
    """

    event_id: str
    rating: int
    text: str


@dataclass(frozen=True)
class DelayReviewMetrics:
    """Input value object for the delay-review detector.

    Attributes
    ----------
    restaurant_id    : Restaurant identifier.
    reviews          : All reviews received in the observation window.
    delay_keywords   : Keyword set for delay-term matching.
    window_start     : UTC-aware window start.
    window_end       : UTC-aware window end.
    """

    restaurant_id: str
    reviews: tuple[ReviewObservation, ...]
    delay_keywords: frozenset[str]
    window_start: datetime
    window_end: datetime


def _contains_delay_term(text: str, keywords: frozenset[str]) -> bool:
    """Return True if any keyword appears in the lowercased text."""
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _classify_count(count: int) -> Severity | None:
    for threshold, severity in _SEVERITY_BRACKETS:
        if count >= threshold:
            return severity
    return None


def detect_delay_review_spike(metrics: DelayReviewMetrics) -> Signal | None:
    """Detect a cluster of negative, delay-mentioning reviews.

    Returns Signal if the trigger fires, None otherwise.
    """
    qualifying = [
        r
        for r in metrics.reviews
        if r.rating <= MAX_QUALIFYING_RATING
        and _contains_delay_term(r.text, metrics.delay_keywords)
    ]

    severity = _classify_count(len(qualifying))
    if severity is None:
        return None

    evidence_ids = tuple(r.event_id for r in qualifying)
    confidence: float = SEVERITY_SCORE[severity]

    current_dec = Decimal(str(len(qualifying)))
    baseline_dec = Decimal("0")          # reviews: no meaningful baseline count
    window_tag = metrics.window_start.strftime("%Y%m%dT%H%M%SZ")
    signal_id = f"sig_delay_review_{metrics.restaurant_id}_{window_tag}"

    return Signal.model_validate(
        {
            "signal_id": signal_id,
            "restaurant_id": metrics.restaurant_id,
            "signal_type": SignalType.DELAY_REVIEW_SPIKE,
            "severity": confidence,
            "current_value": current_dec,
            "baseline_value": baseline_dec,
            "deviation": current_dec - baseline_dec,
            "unit": "qualifying_reviews",
            "window_start": metrics.window_start,
            "window_end": metrics.window_end,
            "evidence_event_ids": evidence_ids,
            "detector_version": DETECTOR_VERSION,
        }
    )
