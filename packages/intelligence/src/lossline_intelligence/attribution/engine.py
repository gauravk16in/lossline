"""Pure C10 driver ranking and attribution assembly."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json

from lossline_intelligence.attribution.models import (
    AttributionInput,
    AttributionMethod,
    DriverDirection,
    DriverEvidence,
)

DRIVER_RULE_VERSION = "driver_attribution.v1"
DEFAULT_MAX_DRIVERS = 5
DEFAULT_NEUTRAL_EPSILON = Decimal("0.0001")
NON_CAUSAL_WORDING_LIMIT = (
    "Associated forecast driver only; do not describe this evidence as causal."
)
_DP = Decimal("0.0001")


def _direction(value: Decimal, epsilon: Decimal) -> DriverDirection:
    if abs(value) <= epsilon:
        return DriverDirection.NEUTRAL
    return DriverDirection.INCREASE if value > 0 else DriverDirection.DECREASE


def attribute_drivers(
    *,
    forecast_id: str,
    candidates: tuple[AttributionInput, ...],
    registered_feature_ids: tuple[str, ...],
    max_drivers: int = DEFAULT_MAX_DRIVERS,
    neutral_epsilon: Decimal = DEFAULT_NEUTRAL_EPSILON,
    rule_version: str = DRIVER_RULE_VERSION,
) -> tuple[DriverEvidence, ...]:
    """Validate, deterministically rank, and materialize structured evidence."""
    if not isinstance(forecast_id, str) or not forecast_id.strip():
        raise ValueError("forecast_id must be non-empty")
    if max_drivers < 1:
        raise ValueError("max_drivers must be positive")
    if not neutral_epsilon.is_finite() or neutral_epsilon < 0:
        raise ValueError("neutral_epsilon must be finite and non-negative")
    if len(set(registered_feature_ids)) != len(registered_feature_ids):
        raise ValueError("registered_feature_ids must be unique")
    registered = set(registered_feature_ids)
    seen_features: set[str] = set()
    validated: list[AttributionInput] = []
    for item in candidates:
        if item.feature_id not in registered:
            raise ValueError(f"unregistered feature_id: {item.feature_id}")
        if item.feature_id in seen_features:
            raise ValueError(f"duplicate feature_id: {item.feature_id}")
        if not item.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        if not item.score.is_finite():
            raise ValueError("score must be finite")
        if item.contribution is not None and not item.contribution.is_finite():
            raise ValueError("contribution must be finite")
        if item.method is AttributionMethod.DETERMINISTIC_DEVIATION and item.contribution is not None:
            raise ValueError("deterministic deviation cannot claim numeric contribution")
        if item.method is AttributionMethod.MODEL_CONTRIBUTION and item.contribution is None:
            raise ValueError("model contribution requires contribution")
        seen_features.add(item.feature_id)
        validated.append(item)

    ordered = sorted(validated, key=lambda item: (-abs(item.score), item.feature_id))[:max_drivers]
    result: list[DriverEvidence] = []
    for rank, item in enumerate(ordered, start=1):
        signed_value = item.contribution if item.contribution is not None else item.score
        payload = {
            "forecast_id": forecast_id,
            "feature_id": item.feature_id,
            "rank": rank,
            "method": item.method.value,
            "evidence_id": item.evidence_id,
            "score": str(item.score.quantize(_DP, rounding=ROUND_HALF_UP)),
            "contribution": None if item.contribution is None else str(item.contribution.quantize(_DP, rounding=ROUND_HALF_UP)),
            "rule_version": rule_version,
        }
        tag = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
        result.append(
            DriverEvidence(
                driver_id=f"drv_{tag}", forecast_id=forecast_id,
                feature_id=item.feature_id, rank=rank,
                direction=_direction(signed_value, neutral_epsilon), method=item.method,
                evidence_id=item.evidence_id, score=abs(item.score),
                contribution=item.contribution, rule_version=rule_version,
                wording_limit=NON_CAUSAL_WORDING_LIMIT,
            )
        )
    return tuple(result)
