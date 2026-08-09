from datetime import timedelta

import pytest

from lossline_intelligence.features import (
    FeatureAvailability,
    FeatureDataType,
    FeatureDefinition,
    FeatureRegistry,
    FeatureRegistryError,
    FeatureTimeSemantics,
    MissingValueStrategy,
)
from lossline_intelligence.signals import SignalCategory


def feature_data() -> dict:
    return {
        "feature_id": "weather.rainfall_forecast_mm",
        "version": "1.0",
        "source": "weather.rainfall_forecast_mm",
        "category": SignalCategory.WEATHER,
        "data_type": FeatureDataType.DECIMAL,
        "unit": "mm",
        "entity_grain": ("outlet_id", "service_window"),
        "time_semantics": FeatureTimeSemantics.FORECAST_VINTAGE,
        "availability": FeatureAvailability.FUTURE_KNOWN,
        "future_known": True,
        "transformation": "latest_vintage_for_target_window",
        "missing_value_strategy": MissingValueStrategy.EXPLICIT_MISSING,
        "max_staleness": timedelta(hours=6),
        "leakage_rationale": "Uses only a provider vintage issued by prediction_as_of.",
    }


def test_registry_exposes_version_and_repeatable_fingerprint() -> None:
    item = FeatureDefinition(**feature_data())
    left = FeatureRegistry((item,), registry_version="features.v1")
    right = FeatureRegistry((item,), registry_version="features.v1")

    assert left.definition_for(item.feature_id) == item
    assert left.registry_version == "features.v1"
    assert left.fingerprint == right.fingerprint
    assert len(left.fingerprint) == 64


def test_fingerprint_is_independent_of_definition_order() -> None:
    weather = FeatureDefinition(**feature_data())
    weekday = FeatureDefinition(
        **(
            feature_data()
            | {
                "feature_id": "calendar.weekday",
                "source": "calendar",
                "category": SignalCategory.CALENDAR,
                "data_type": FeatureDataType.INTEGER,
                "unit": "weekday_index",
                "entity_grain": ("outlet_id", "service_window"),
                "time_semantics": FeatureTimeSemantics.SCHEDULED_FUTURE,
                "transformation": "outlet_local_weekday",
                "max_staleness": None,
                "leakage_rationale": "Calendar value is deterministically known in advance.",
            }
        )
    )

    left = FeatureRegistry((weather, weekday), registry_version="features.v1")
    right = FeatureRegistry((weekday, weather), registry_version="features.v1")

    assert left.fingerprint == right.fingerprint


def test_registry_rejects_empty_duplicate_and_unknown_features() -> None:
    item = FeatureDefinition(**feature_data())
    with pytest.raises(FeatureRegistryError, match="cannot be empty"):
        FeatureRegistry((), registry_version="features.v1")
    with pytest.raises(FeatureRegistryError, match="duplicate"):
        FeatureRegistry((item, item), registry_version="features.v1")
    with pytest.raises(FeatureRegistryError, match="unregistered"):
        FeatureRegistry((item,), registry_version="features.v1").definition_for(
            "weather.actual_rainfall_mm"
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"entity_grain": ()},
        {"entity_grain": ("outlet_id", "outlet_id")},
        {"max_staleness": timedelta(seconds=-1)},
        {"availability": FeatureAvailability.AT_PREDICTION_TIME},
        {"future_known": False},
        {
            "time_semantics": FeatureTimeSemantics.OBSERVED,
            "availability": FeatureAvailability.FUTURE_KNOWN,
            "future_known": True,
        },
    ],
)
def test_definition_rejects_incoherent_semantics(overrides: dict) -> None:
    with pytest.raises(ValueError):
        FeatureDefinition(**(feature_data() | overrides))


def test_historical_feature_is_not_future_known() -> None:
    lag = FeatureDefinition(
        **(
            feature_data()
            | {
                "feature_id": "demand.lag_7",
                "source": "actual_demand",
                "category": SignalCategory.DEMAND,
                "unit": "portion",
                "time_semantics": FeatureTimeSemantics.HISTORICAL_LAG,
                "availability": FeatureAvailability.HISTORICAL_ONLY,
                "future_known": False,
                "transformation": "lag_named_window_7_days",
                "max_staleness": timedelta(days=8),
                "leakage_rationale": "Reads only matured demand before prediction_as_of.",
            }
        )
    )

    assert lag.future_known is False
    assert lag.availability is FeatureAvailability.HISTORICAL_ONLY

