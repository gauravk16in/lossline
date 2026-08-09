from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ComparablePeriod:
    period_id: str
    outlet_id: str
    service_window: str
    window_start: datetime
    sku_id: str | None
    risk_type: str | None
    summary: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    text: str
    effective_from: datetime
    effective_to: datetime | None
    metadata_id: str


@dataclass(frozen=True)
class RetrievedItem:
    item_id: str
    source_type: str
    score: Decimal
    summary: str
    evidence_ids: tuple[str, ...]
