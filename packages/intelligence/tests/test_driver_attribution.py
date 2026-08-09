from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from lossline_intelligence.attribution import (
    AttributionInput, AttributionMethod, DriverDirection, DriverEvidence, attribute_drivers,
)

FEATURES = ("weather.rainfall_mm", "promotion.discount_pct", "demand.fulfilled_quantity.lag1")


def _candidate(feature: str, score: str, *, method=AttributionMethod.DETERMINISTIC_DEVIATION, contribution=None):
    return AttributionInput(feature, f"snap_{feature}", Decimal(score), method, None if contribution is None else Decimal(contribution))


def test_ranks_by_absolute_score_then_feature_id() -> None:
    result = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(
        _candidate(FEATURES[0], "0.4"), _candidate(FEATURES[1], "-0.8"), _candidate(FEATURES[2], "0.4"),
    ))
    assert tuple(item.feature_id for item in result) == (FEATURES[1], FEATURES[2], FEATURES[0])
    assert tuple(item.rank for item in result) == (1, 2, 3)


def test_deterministic_direction_and_no_contribution() -> None:
    item = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[1], "-2"),))[0]
    assert item.direction is DriverDirection.DECREASE
    assert item.contribution is None


def test_model_contribution_controls_direction() -> None:
    item = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(
        _candidate(FEATURES[0], "3", method=AttributionMethod.MODEL_CONTRIBUTION, contribution="-1.2"),
    ))[0]
    assert item.direction is DriverDirection.DECREASE
    assert item.contribution == Decimal("-1.2000")


def test_neutral_boundary() -> None:
    item = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[0], "0.0001"),))[0]
    assert item.direction is DriverDirection.NEUTRAL


def test_limit_and_empty_are_deterministic() -> None:
    candidates = tuple(_candidate(feature, str(index + 1)) for index, feature in enumerate(FEATURES))
    assert len(attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=candidates, max_drivers=2)) == 2
    assert attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=()) == ()


def test_repeatability_and_changed_evidence_identity() -> None:
    candidates = (_candidate(FEATURES[0], "1"),)
    first = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=candidates)
    second = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=candidates)
    changed = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(AttributionInput(FEATURES[0], "other", Decimal("1"), AttributionMethod.DETERMINISTIC_DEVIATION),))
    assert first == second
    assert first[0].driver_id != changed[0].driver_id


@pytest.mark.parametrize("score", [Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_score_rejected(score: Decimal) -> None:
    with pytest.raises(ValueError, match="finite"):
        attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(AttributionInput(FEATURES[0], "e1", score, AttributionMethod.DETERMINISTIC_DEVIATION),))


def test_unregistered_and_duplicate_features_rejected() -> None:
    with pytest.raises(ValueError, match="unregistered"):
        attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate("unknown", "1"),))
    with pytest.raises(ValueError, match="duplicate feature_id"):
        attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[0], "1"), _candidate(FEATURES[0], "2")))


def test_method_contribution_contracts_rejected() -> None:
    with pytest.raises(ValueError, match="cannot claim"):
        attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[0], "1", contribution="1"),))
    with pytest.raises(ValueError, match="requires contribution"):
        attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[0], "1", method=AttributionMethod.MODEL_CONTRIBUTION),))


def test_contract_is_frozen_strict_and_non_causal() -> None:
    item = attribute_drivers(forecast_id="fc1", registered_feature_ids=FEATURES, candidates=(_candidate(FEATURES[0], "1"),))[0]
    assert "do not describe" in item.wording_limit
    with pytest.raises(ValidationError):
        DriverEvidence(**(item.model_dump() | {"extra": "bad"}))
    with pytest.raises(ValidationError):
        item.rank = 2
