from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.signals import (
    DecimalValue,
    EntityType,
    ForecastSafetyError,
    NormalizedSignal,
    RegistryError,
    SignalCategory,
    SignalDefinition,
    SignalProvenance,
    SignalQuality,
    SignalRegistry,
    ValueKind,
)


AS_OF = datetime(2026, 8, 9, 4, 30, tzinfo=timezone.utc)


def definition_data() -> dict:
    return {
        "signal_type": "weather.rainfall_forecast_mm",
        "version": "1.0",
        "category": SignalCategory.WEATHER,
        "entity_type": EntityType.WEATHER_REGION,
        "value_kind": ValueKind.DECIMAL,
        "unit": "mm",
        "forecast_safe": True,
        "max_staleness": timedelta(hours=6),
        "leakage_rationale": "Provider forecast vintage is known before service.",
        "allowed_sources": ("weather_provider",),
    }


def signal_data() -> dict:
    return {
        "schema_version": "1.0",
        "signal_id": "obs_weather_1",
        "outlet_id": "outlet_1",
        "entity_type": EntityType.WEATHER_REGION,
        "entity_id": "region_1",
        "observed_at": AS_OF - timedelta(hours=1),
        "effective_from": AS_OF + timedelta(hours=3),
        "source": "weather_provider",
        "category": SignalCategory.WEATHER,
        "signal_type": "weather.rainfall_forecast_mm",
        "value": DecimalValue(value=Decimal("4.2")),
        "unit": "mm",
        "quality": SignalQuality(
            completeness=Decimal("1"), validity=Decimal("1"),
            freshness=Decimal("1"), source_confidence=Decimal("0.8"),
        ),
        "provenance": SignalProvenance(
            provider="weather_provider", source_record_id="wx_1",
            ingested_at=AS_OF - timedelta(minutes=55),
            transformation_version="weather_v1",
        ),
    }


def registry(**overrides: object) -> SignalRegistry:
    return SignalRegistry((SignalDefinition(**(definition_data() | overrides)),))


def signal(**overrides: object) -> NormalizedSignal:
    return NormalizedSignal.model_validate(signal_data() | overrides)


def test_registry_accepts_matching_contract_repeatably() -> None:
    item = signal()
    first = registry().require_forecast_safe(item, prediction_as_of=AS_OF)
    second = registry().require_forecast_safe(item, prediction_as_of=AS_OF)

    assert first == second
    assert first.signal_type == item.signal_type


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unit", "celsius"),
        ("category", SignalCategory.DEMAND),
        ("entity_type", EntityType.SKU),
        ("source", "actual_weather_station"),
    ],
)
def test_registry_rejects_semantic_mismatch(field: str, value: object) -> None:
    with pytest.raises(RegistryError):
        registry().validate(signal(**{field: value}))


def test_registry_rejects_unknown_and_duplicate_types() -> None:
    with pytest.raises(RegistryError, match="unregistered"):
        registry().validate(signal(signal_type="weather.unknown"))
    item = SignalDefinition(**definition_data())
    with pytest.raises(RegistryError, match="duplicate"):
        SignalRegistry((item, item))


def test_forecast_safety_excludes_future_observation() -> None:
    item = signal(
        observed_at=AS_OF + timedelta(minutes=1),
        provenance=signal_data()["provenance"].model_copy(
            update={"ingested_at": AS_OF + timedelta(minutes=2)}
        ),
    )
    with pytest.raises(ForecastSafetyError, match="not observed"):
        registry().require_forecast_safe(item, prediction_as_of=AS_OF)


def test_forecast_safety_excludes_late_ingestion() -> None:
    item = signal(
        provenance=signal_data()["provenance"].model_copy(
            update={"ingested_at": AS_OF + timedelta(seconds=1)}
        )
    )
    with pytest.raises(ForecastSafetyError, match="not ingested"):
        registry().require_forecast_safe(item, prediction_as_of=AS_OF)


def test_forecast_safety_accepts_at_boundary_and_rejects_stale() -> None:
    boundary = signal(
        observed_at=AS_OF - timedelta(hours=6),
        provenance=signal_data()["provenance"].model_copy(
            update={"ingested_at": AS_OF - timedelta(hours=5, minutes=59)}
        ),
    )
    registry().require_forecast_safe(boundary, prediction_as_of=AS_OF)

    stale = signal(
        observed_at=AS_OF - timedelta(hours=6, seconds=1),
        provenance=signal_data()["provenance"].model_copy(
            update={"ingested_at": AS_OF - timedelta(hours=6)}
        ),
    )
    with pytest.raises(ForecastSafetyError, match="staleness"):
        registry().require_forecast_safe(stale, prediction_as_of=AS_OF)


def test_forecast_safety_rejects_registered_outcome_and_naive_as_of() -> None:
    unsafe = registry(forecast_safe=False)
    with pytest.raises(ForecastSafetyError, match="not forecast-safe"):
        unsafe.require_forecast_safe(signal(), prediction_as_of=AS_OF)
    with pytest.raises(ForecastSafetyError, match="UTC offset"):
        registry().require_forecast_safe(signal(), prediction_as_of=AS_OF.replace(tzinfo=None))

