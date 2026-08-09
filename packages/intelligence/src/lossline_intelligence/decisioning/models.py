"""C13 strict decision-submission contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_DP = Decimal("0.0001")


class DecisionAction(StrEnum):
    NO_ACTION = "NO_ACTION"
    ABSTAIN = "ABSTAIN"
    ADJUST_PREP_QUANTITY = "ADJUST_PREP_QUANTITY"
    REALLOCATE_STAFF = "REALLOCATE_STAFF"
    PAUSE_DELIVERY_SKU = "PAUSE_DELIVERY_SKU"


class RiskType(StrEnum):
    INVENTORY_SHORTAGE = "INVENTORY_SHORTAGE"
    INVENTORY_SURPLUS = "INVENTORY_SURPLUS"
    CAPACITY_OVERLOAD = "CAPACITY_OVERLOAD"
    DELIVERY_OVERSELL = "DELIVERY_OVERSELL"
    NONE = "NONE"


class Urgency(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActionRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DecisionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: Identifier
    decision_version: Identifier
    dossier_id: Identifier
    forecast_id: Identifier
    outlet_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    risk_type: RiskType
    sku_id: Identifier | None = None
    action: DecisionAction
    quantity: Decimal | None = None
    unit: Identifier | None = None
    execute_by: datetime | None = None
    reason_code: Identifier
    evidence_ids: tuple[Identifier, ...]
    urgency: Urgency
    action_risk: ActionRisk
    approval_required: bool
    constraints_considered: tuple[Identifier, ...] = ()

    @field_validator("window_start", "window_end", "execute_by")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("quantity")
    @classmethod
    def finite_quantity(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite() or value < 0:
            raise ValueError("quantity must be finite and non-negative")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def consistency(self) -> "DecisionCandidate":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique")
        if len(set(self.constraints_considered)) != len(self.constraints_considered):
            raise ValueError("constraints_considered must be unique")
        if (self.quantity is None) != (self.unit is None):
            raise ValueError("quantity and unit must be supplied together")
        if self.action in (DecisionAction.NO_ACTION, DecisionAction.ABSTAIN) and self.quantity is not None:
            raise ValueError("NO_ACTION and ABSTAIN cannot carry quantity")
        return self


class DecisionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: Annotated[str, Field(pattern=r"^submit_operational_decision$")]
    arguments: DecisionCandidate
