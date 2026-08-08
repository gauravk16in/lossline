from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lossline_intelligence.models.signal import Signal, SignalType


def signal_data() -> dict[str, object]:
    return {
        "signal_id": "sig_001",
        "outlet_id": "store_17",
        "signal_type": SignalType.CANCELLATION_SPIKE,
        "severity": 0.72,
        "current_value": Decimal("0.12"),
        "baseline_value": Decimal("0.04"),
        "deviation_ratio": Decimal("2"),
        "unit": "ratio",
        "window_start": datetime(2026, 8, 8, 7, 30, tzinfo=timezone.utc),
        "window_end": datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc),
        "evidence_event_ids": ("evt_001", "evt_002"),
        "detector_version": "cancellation_spike.v1",
        "metadata": {
            "sample_size": 42,
            "threshold": 0.08,
            "baseline_method": "median_same_window_7d",
        },
    }


def test_signal_accepts_valid_detector_output() -> None:
    signal = Signal.model_validate(signal_data())

    assert signal.signal_type is SignalType.CANCELLATION_SPIKE
    assert signal.outlet_id == "store_17"
    assert signal.deviation_ratio == Decimal("2")
    assert signal.metadata["sample_size"] == 42
    assert signal.severity == 0.72
    assert signal.window_start.tzinfo is timezone.utc


def test_signal_defaults_metadata_to_empty_dict() -> None:
    data = signal_data()
    del data["metadata"]

    signal = Signal.model_validate(data)

    assert signal.metadata == {}


@pytest.mark.parametrize("severity", [-0.01, 1.01, float("nan")])
def test_signal_rejects_invalid_severity(severity: float) -> None:
    data = signal_data() | {"severity": severity}

    with pytest.raises(ValidationError):
        Signal.model_validate(data)


def test_signal_normalizes_offset_timestamps_to_utc() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    data = signal_data() | {
        "window_start": datetime(2026, 8, 8, 13, 0, tzinfo=offset),
        "window_end": datetime(2026, 8, 8, 13, 30, tzinfo=offset),
    }

    signal = Signal.model_validate(data)

    assert signal.window_start == datetime(2026, 8, 8, 7, 30, tzinfo=timezone.utc)
    assert signal.window_end == datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc)


def test_signal_rejects_empty_or_duplicate_evidence() -> None:
    for evidence in [(), ("evt_001", "evt_001")]:
        with pytest.raises(ValidationError):
            Signal.model_validate(signal_data() | {"evidence_event_ids": evidence})


def test_signal_rejects_reversed_window() -> None:
    data = signal_data() | {
        "window_start": datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc),
        "window_end": datetime(2026, 8, 8, 7, 30, tzinfo=timezone.utc),
    }

    with pytest.raises(ValidationError):
        Signal.model_validate(data)
