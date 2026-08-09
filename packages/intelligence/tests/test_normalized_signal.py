from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lossline_intelligence.signals import (
    DecimalValue,
    EntityType,
    JsonValue,
    NormalizedSignal,
    SignalCategory,
    SignalProvenance,
    SignalQuality,
)


NOW = datetime(2026, 8, 9, 4, 30, tzinfo=timezone.utc)


def signal_data() -> dict:
    return {
        "schema_version": "1.0",
        "signal_id": "obs_1",
        "outlet_id": "outlet_1",
        "entity_type": EntityType.SKU,
        "entity_id": "sku_1",
        "observed_at": NOW,
        "effective_from": NOW + timedelta(hours=3),
        "effective_until": NOW + timedelta(hours=4),
        "source": "weather_provider",
        "category": SignalCategory.WEATHER,
        "signal_type": "weather.rainfall_forecast_mm",
        "value": DecimalValue(value=Decimal("12.5")),
        "unit": "mm",
        "dimensions": {"service_window": "LUNCH"},
        "quality": SignalQuality(
            completeness=Decimal("1"),
            validity=Decimal("1"),
            freshness=Decimal("0.9"),
            source_confidence=Decimal("0.8"),
        ),
        "provenance": SignalProvenance(
            provider="weather_provider",
            source_record_id="forecast_1",
            ingested_at=NOW + timedelta(minutes=1),
            transformation_version="weather_v1",
        ),
    }


def test_normalized_signal_accepts_future_effective_value_known_now() -> None:
    signal = NormalizedSignal.model_validate(signal_data())

    assert signal.observed_at == NOW
    assert signal.effective_from > signal.observed_at
    assert signal.value.kind == "DECIMAL"


def test_normalized_signal_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="UTC offset"):
        NormalizedSignal.model_validate(
            signal_data() | {"observed_at": datetime(2026, 8, 9, 10, 0)}
        )


def test_normalized_signal_rejects_invalid_effective_window() -> None:
    with pytest.raises(ValidationError, match="effective_until must be after"):
        NormalizedSignal.model_validate(
            signal_data() | {"effective_until": NOW + timedelta(hours=2)}
        )


def test_normalized_signal_rejects_ingestion_before_observation() -> None:
    provenance = signal_data()["provenance"].model_copy(
        update={"ingested_at": NOW - timedelta(seconds=1)}
    )
    with pytest.raises(ValidationError, match="ingested_at cannot be before"):
        NormalizedSignal.model_validate(signal_data() | {"provenance": provenance})


def test_decimal_and_quality_values_must_be_finite() -> None:
    with pytest.raises(ValidationError, match="finite"):
        DecimalValue(value=Decimal("NaN"))
    with pytest.raises(ValidationError, match="finite"):
        SignalQuality(
            completeness=Decimal("NaN"),
            validity=Decimal("1"),
            freshness=Decimal("1"),
            source_confidence=Decimal("1"),
        )


def test_json_values_are_bounded_and_do_not_accept_floats() -> None:
    with pytest.raises(ValidationError, match="cannot contain floats"):
        JsonValue(value={"rainfall": 1.5})
    nested: dict = {"value": 1}
    for index in range(9):
        nested = {f"level_{index}": nested}
    with pytest.raises(ValidationError, match="8 levels"):
        JsonValue(value=nested)
