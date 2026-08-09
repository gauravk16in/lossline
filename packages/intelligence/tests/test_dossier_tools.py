from datetime import datetime, timezone

import pytest

from lossline_intelligence.dossiers import ArtifactRef, CuratedSummary, DataQualitySummary, build_forecast_dossier
from lossline_intelligence.tools import DossierToolbox, ToolBudgetExceeded, ToolLookupError

T0 = datetime(2026, 1, 7, 10, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 7, 13, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 7, 16, tzinfo=timezone.utc)


def _ref(identifier, kind): return ArtifactRef(artifact_id=identifier, artifact_type=kind, version="v1")


def _dossier():
    return build_forecast_dossier(
        outlet_id="out1", service_window="DINNER", window_start=T1, window_end=T2,
        prediction_as_of=T0, forecast_refs=(_ref("fc1", "forecast"),),
        feature_snapshot_refs=(_ref("snap1", "snapshot"),),
        driver_refs=(_ref("drv1", "driver"),), data_quality=DataQualitySummary(tier="HIGH"),
        similar_periods=(CuratedSummary(summary_id="sim1", summary_type="similar",
            text="Comparable Friday", evidence_ids=("fc_old",)),),
    )


def test_reads_only_dossier_members() -> None:
    tools = DossierToolbox(_dossier())
    assert tools.get_artifact_ref("fc1").value.artifact_id == "fc1"
    assert tools.get_curated_summary("sim1").value.text == "Comparable Friday"
    with pytest.raises(ToolLookupError, match="not a member"):
        tools.get_artifact_ref("outside")


def test_budget_counts_success_and_failed_lookup() -> None:
    tools = DossierToolbox(_dossier(), read_budget=2)
    tools.get_artifact_ref("fc1")
    with pytest.raises(ToolLookupError): tools.get_artifact_ref("outside")
    assert tools.reads_used == 2
    with pytest.raises(ToolBudgetExceeded): tools.get_artifact_ref("snap1")


def test_zero_budget_and_invalid_budget() -> None:
    with pytest.raises(ValueError): DossierToolbox(_dossier(), read_budget=-1)
    tools = DossierToolbox(_dossier(), read_budget=0)
    with pytest.raises(ToolBudgetExceeded): tools.get_artifact_ref("fc1")


def test_trace_is_immutable_and_repeatable() -> None:
    tools = DossierToolbox(_dossier())
    tools.get_artifact_ref("drv1")
    assert tools.trace == (("get_artifact_ref", "drv1"),)
    assert isinstance(tools.trace, tuple)


def test_results_and_sources_are_frozen() -> None:
    tools = DossierToolbox(_dossier())
    result = tools.get_artifact_ref("fc1")
    with pytest.raises(Exception): result.result_id = "changed"
    with pytest.raises(Exception): result.value.artifact_id = "changed"


def test_toolbox_has_no_raw_store_or_write_surface() -> None:
    names = set(dir(DossierToolbox))
    assert not names.intersection({"query", "execute", "write", "save", "get_raw_events", "get_provider_payload"})
