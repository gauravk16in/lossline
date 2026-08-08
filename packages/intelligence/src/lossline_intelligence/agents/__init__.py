"""Specialist agents for LOSSLine deterministic intelligence.

Each agent takes a metrics input and returns a Signal | None.
No LLM, no I/O, no side effects.
"""

from lossline_intelligence.agents.cancellation import (
    CancellationMetrics,
    CancellationSignal,
    detect_cancellation_spike,
)
from lossline_intelligence.agents.delay_review import (
    DEFAULT_DELAY_KEYWORDS,
    DelayReviewMetrics,
    ReviewObservation,
    detect_delay_review_spike,
)
from lossline_intelligence.agents.handoff_delay import (
    HandoffDelayMetrics,
    detect_handoff_delay_spike,
)
from lossline_intelligence.agents.order_volume import (
    OrderVolumeMetrics,
    detect_order_volume_spike,
)
from lossline_intelligence.agents.prep_time import (
    PrepTimeMetrics,
    detect_prep_time_spike,
)

__all__ = [
    "CancellationMetrics",
    "CancellationSignal",
    "detect_cancellation_spike",
    "OrderVolumeMetrics",
    "detect_order_volume_spike",
    "PrepTimeMetrics",
    "detect_prep_time_spike",
    "HandoffDelayMetrics",
    "detect_handoff_delay_spike",
    "DelayReviewMetrics",
    "ReviewObservation",
    "DEFAULT_DELAY_KEYWORDS",
    "detect_delay_review_spike",
]
