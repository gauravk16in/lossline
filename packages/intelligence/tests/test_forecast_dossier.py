from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lossline_intelligence.dossiers import (
    ArtifactRef, ConstraintSummary, CuratedSummary, DataQualitySummary,
    HistoricalPerformanceSummary, build_forecast_dossier,
)

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def ref(identifier: str, kind: str = "forecast") -> ArtifactRef:
    return ArtifactRef(artifact_id=identifier, artifact_type=kind, version="v1")


def dossier(**overrides):
    values = dict(
        outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        prediction_as_of=T0, forecast_refs=(ref("fc1"),),
        feature_snapshot_refs=(ref("snap1", "feature_snapshot"),),
        inventory_refs=(ref("inv1", "inventory_projection"),),
        capacity_refs=(ref("cap1", "capacity_projection"),),
        driver_refs=(ref("drv1", "driver_evidence"),),
        historical_performance=(HistoricalPerformanceSummary(
            evaluation_id="eval1", sample_count=20, mae=Decimal("2.3"),
            wmape=Decimal("0.1"), interval_coverage=Decimal("0.8")),),
        similar_periods=(CuratedSummary(summary_id="sim1", summary_type="similar_period",
            text="Comparable Friday dinner", evidence_ids=("eval1",)),),
        previous_decisions=(CuratedSummary(summary_id="dec1", summary_type="previous_decision",
            text="Manager approved a bounded prep adjustment", evidence_ids=("decision1",)),),
        constraints=(ConstraintSummary(constraint_id="con1", constraint_type="STAFFING",
            description="No additional trained cook available", evidence_id="policy1"),),
        policy_refs=(ref("policy1", "policy"),),
        data_quality=DataQualitySummary(tier="HIGH"), provenance_ids=("signal1",),
    )
    values.update(overrides)
    return build_forecast_dossier(**values)


def test_complete_dossier_and_refs() -> None:
    item = dossier()
    assert item.dossier_id.startswith("dos_")
    assert item.capacity_refs[0].artifact_id == "cap1"
    assert item.driver_refs[0].artifact_id == "drv1"


def test_repeatability_excludes_created_at() -> None:
    assert dossier(created_at=T0).dossier_id == dossier(created_at=T1).dossier_id


def test_changed_decision_relevant_input_changes_id() -> None:
    assert dossier().dossier_id != dossier(provenance_ids=("signal2",)).dossier_id


def test_contract_is_frozen_and_strict() -> None:
    item = dossier()
    with pytest.raises(ValidationError):
        item.outlet_id = "other"
    with pytest.raises(ValidationError):
        item.__class__(**(item.model_dump() | {"raw_events": []}))


def test_raw_payload_has_no_contract_path() -> None:
    fields = set(type(dossier()).model_fields)
    assert not fields.intersection({"raw_events", "database_rows", "provider_payload", "gold_decision", "actual_outcome"})


def test_required_refs_and_window_rules() -> None:
    with pytest.raises(ValidationError, match="requires forecast"):
        dossier(forecast_refs=())
    with pytest.raises(ValidationError, match="after window_start"):
        dossier(window_end=T1)
    with pytest.raises(ValidationError, match="must not be after"):
        dossier(prediction_as_of=T2)


def test_naive_time_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        dossier(window_start=datetime(2026, 1, 7, 13))


def test_duplicate_artifact_and_provenance_rejected() -> None:
    with pytest.raises(ValidationError, match="artifact references must be unique"):
        dossier(driver_refs=(ref("fc1", "driver"),))
    with pytest.raises(ValidationError, match="provenance_ids must be unique"):
        dossier(provenance_ids=("s1", "s1"))


def test_quality_and_summary_collections_are_immutable_tuples() -> None:
    item = dossier(data_quality=DataQualitySummary(tier="LOW", missing_feature_ids=("f1",)))
    assert item.data_quality.missing_feature_ids == ("f1",)
    assert isinstance(item.similar_periods, tuple)


def test_performance_validation() -> None:
    with pytest.raises(ValidationError, match="sample_count"):
        HistoricalPerformanceSummary(evaluation_id="e", sample_count=0, mae=Decimal("1"))
    with pytest.raises(ValidationError, match="<= 1"):
        HistoricalPerformanceSummary(evaluation_id="e", sample_count=1, mae=Decimal("1"), interval_coverage=Decimal("1.1"))
    with pytest.raises(ValidationError, match="finite"):
        HistoricalPerformanceSummary(evaluation_id="e", sample_count=1, mae=Decimal("NaN"))


def test_duplicate_summary_evidence_rejected() -> None:
    with pytest.raises(ValidationError, match="unique"):
        CuratedSummary(summary_id="s", summary_type="similar", text="text", evidence_ids=("e", "e"))
