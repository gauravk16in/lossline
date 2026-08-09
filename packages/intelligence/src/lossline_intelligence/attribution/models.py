"""C10 attribution contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_DP = Decimal("0.0001")


class AttributionMethod(StrEnum):
    DETERMINISTIC_DEVIATION = "DETERMINISTIC_DEVIATION"
    MODEL_CONTRIBUTION = "MODEL_CONTRIBUTION"


class DriverDirection(StrEnum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class AttributionInput:
    """Internal candidate already computed by deterministic/model-owned code."""

    feature_id: str
    evidence_id: str
    score: Decimal
    method: AttributionMethod
    contribution: Decimal | None = None


class DriverEvidence(BaseModel):
    """Validated attribution artifact; it describes association, never causality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    driver_id: Identifier
    forecast_id: Identifier
    feature_id: Identifier
    rank: int
    direction: DriverDirection
    method: AttributionMethod
    evidence_id: Identifier
    score: Decimal
    contribution: Decimal | None = None
    rule_version: Identifier
    wording_limit: str

    @field_validator("score", "contribution")
    @classmethod
    def finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite():
            raise ValueError("attribution values must be finite")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_semantics(self) -> "DriverEvidence":
        if self.rank < 1:
            raise ValueError("rank must be positive")
        if self.score < 0:
            raise ValueError("score must be non-negative")
        if self.method is AttributionMethod.DETERMINISTIC_DEVIATION and self.contribution is not None:
            raise ValueError("deterministic deviation does not support numeric contribution")
        if self.method is AttributionMethod.MODEL_CONTRIBUTION and self.contribution is None:
            raise ValueError("model contribution requires a numeric contribution")
        return self
