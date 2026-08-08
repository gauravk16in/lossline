"""Shared factories for detector tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lossline_intelligence.aggregation.baseline import (
    BASELINE_VERSION,
    BaselineResult,
    MetricBaseline,
)
from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot

W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
W_END = W_START + timedelta(minutes=30)
OUTLET = "outlet_test"


def mb(
    median: str | None,
    *,
    mad: str | None = None,
    sample_count: int = 5,
) -> MetricBaseline:
    med = Decimal(median) if median is not None else None
    if mad is not None:
        mad_val = Decimal(mad)
    elif med is not None:
        mad_val = Decimal("0.5000")
    else:
        mad_val = None
    return MetricBaseline(median=med, mad=mad_val, sample_count=sample_count)


def empty_mb() -> MetricBaseline:
    return MetricBaseline(median=None, mad=None, sample_count=0)


def snap(**overrides) -> MetricSnapshot:
    base = {
        "outlet_id": OUTLET,
        "window_start": W_START,
        "window_end": W_END,
        "order_count": 20,
        "delivery_order_count": 0,
        "cancelled_order_count": 0,
        "cancellation_rate": Decimal("0.0000"),
        "avg_prep_minutes": Decimal("0"),
        "p90_prep_minutes": Decimal("0"),
        "prep_completed_count": 0,
        "avg_handoff_wait_minutes": Decimal("0"),
        "handoff_completed_count": 0,
        "review_count": 0,
        "negative_review_count": 0,
        "delay_review_count": 0,
        "delay_review_event_ids": (),
        "source_event_ids": ("evt_001", "evt_002"),
    }
    base.update(overrides)
    return MetricSnapshot.model_validate(base)


def baseline(**overrides) -> BaselineResult:
    empty = empty_mb()
    base = {
        "outlet_id": OUTLET,
        "sample_count": 5,
        "sufficient_history": True,
        "baseline_version": BASELINE_VERSION,
        "order_count": mb("18.0000", mad="1.0000"),
        "cancellation_rate": empty,
        "avg_prep_minutes": empty,
        "p90_prep_minutes": empty,
        "avg_handoff_wait_minutes": empty,
        "negative_review_rate": empty,
        "delay_review_rate": empty,
    }
    base.update(overrides)
    return BaselineResult(**base)
