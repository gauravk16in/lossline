"""Signal correlation layer for LOSSLine intelligence."""

from lossline_intelligence.correlation.engine import correlate_signals
from lossline_intelligence.correlation.rules import (
    CORRELATION_RULE_ID,
    CORRELATION_RULE_VERSION,
    MAX_GAP_MINUTES,
    REQUIRED_SIGNAL_TYPES,
    SUPPORTING_SIGNAL_TYPES,
)

__all__ = [
    "correlate_signals",
    "CORRELATION_RULE_ID",
    "CORRELATION_RULE_VERSION",
    "MAX_GAP_MINUTES",
    "REQUIRED_SIGNAL_TYPES",
    "SUPPORTING_SIGNAL_TYPES",
]
