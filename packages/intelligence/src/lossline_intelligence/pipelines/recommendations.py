"""Backward-compatible re-export — canonical implementation is in recommendations/."""

from lossline_intelligence.recommendations.engine import (
    Recommendation,
    recommend_action,
)
from lossline_intelligence.recommendations.playbooks import (
    CONFIDENCE_THRESHOLD,
    OPERATIONAL_OVERLOAD_V1,
)

RULE_ID = OPERATIONAL_OVERLOAD_V1.rule_id
RECOMMENDATION_VERSION = OPERATIONAL_OVERLOAD_V1.rule_version

__all__ = [
    "recommend_action",
    "Recommendation",
    "CONFIDENCE_THRESHOLD",
    "RULE_ID",
    "RECOMMENDATION_VERSION",
]
