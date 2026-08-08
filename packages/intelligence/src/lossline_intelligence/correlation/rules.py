"""Correlation rule definitions for M1 lunch-rush operational overload."""

from lossline_intelligence.models.signal import SignalType

#: Stable rule identifier embedded in incident candidates.
CORRELATION_RULE_ID: str = "OPERATIONAL_OVERLOAD_V1"

#: Versioned configuration for cache invalidation and dedup fingerprints.
CORRELATION_RULE_VERSION: str = "overload_v1"

#: Maximum minutes between earliest window_start and any signal window_end.
#: CONFIG_DEFAULT — FINAL_IMPLEMENTATION_PLAN.md §Incident Correlation.
MAX_GAP_MINUTES: float = 60.0

#: Signals that must all be present to create a candidate.
REQUIRED_SIGNAL_TYPES: frozenset[SignalType] = frozenset(
    {
        SignalType.ORDER_VOLUME_SPIKE,
        SignalType.PREP_TIME_SPIKE,
        SignalType.CANCELLATION_SPIKE,
    }
)

#: Optional signals preserved on the candidate when present and aligned.
SUPPORTING_SIGNAL_TYPES: frozenset[SignalType] = frozenset(
    {
        SignalType.HANDOFF_DELAY_SPIKE,
        SignalType.DELAY_REVIEW_SPIKE,
    }
)

ALL_CORRELATED_TYPES: frozenset[SignalType] = (
    REQUIRED_SIGNAL_TYPES | SUPPORTING_SIGNAL_TYPES
)
