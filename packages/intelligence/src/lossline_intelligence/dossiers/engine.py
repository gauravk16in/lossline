"""Deterministic C11 dossier builder."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

from lossline_intelligence.dossiers.models import (
    ArtifactRef, ConstraintSummary, CuratedSummary, DataQualitySummary,
    ForecastDossier, HistoricalPerformanceSummary,
)

DOSSIER_VERSION = "forecast_dossier.v1"


def build_forecast_dossier(
    *, outlet_id: str, service_window: str, window_start: datetime, window_end: datetime,
    prediction_as_of: datetime, forecast_refs: tuple[ArtifactRef, ...],
    feature_snapshot_refs: tuple[ArtifactRef, ...], data_quality: DataQualitySummary,
    inventory_refs: tuple[ArtifactRef, ...] = (), capacity_refs: tuple[ArtifactRef, ...] = (),
    risk_refs: tuple[ArtifactRef, ...] = (), driver_refs: tuple[ArtifactRef, ...] = (),
    historical_performance: tuple[HistoricalPerformanceSummary, ...] = (),
    similar_periods: tuple[CuratedSummary, ...] = (),
    previous_decisions: tuple[CuratedSummary, ...] = (),
    constraints: tuple[ConstraintSummary, ...] = (), policy_refs: tuple[ArtifactRef, ...] = (),
    provenance_ids: tuple[str, ...] = (), dossier_version: str = DOSSIER_VERSION,
    created_at: datetime | None = None,
) -> ForecastDossier:
    """Assemble typed references and curated summaries; raw records are not accepted."""
    created = created_at or prediction_as_of
    identity = {
        "version": dossier_version, "outlet": outlet_id, "window": service_window,
        "start": window_start.astimezone(timezone.utc).isoformat() if window_start.tzinfo else str(window_start),
        "end": window_end.astimezone(timezone.utc).isoformat() if window_end.tzinfo else str(window_end),
        "as_of": prediction_as_of.astimezone(timezone.utc).isoformat() if prediction_as_of.tzinfo else str(prediction_as_of),
        "refs": [ref.model_dump(mode="json") for refs in (forecast_refs, feature_snapshot_refs, inventory_refs, capacity_refs, risk_refs, driver_refs, policy_refs) for ref in refs],
        "performance": [item.model_dump(mode="json") for item in historical_performance],
        "similar": [item.model_dump(mode="json") for item in similar_periods],
        "previous": [item.model_dump(mode="json") for item in previous_decisions],
        "constraints": [item.model_dump(mode="json") for item in constraints],
        "quality": data_quality.model_dump(mode="json"), "provenance": provenance_ids,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    dossier_id = f"dos_{sha256(encoded).hexdigest()[:16]}"
    return ForecastDossier(
        dossier_id=dossier_id, dossier_version=dossier_version, outlet_id=outlet_id,
        service_window=service_window, window_start=window_start, window_end=window_end,
        prediction_as_of=prediction_as_of, forecast_refs=forecast_refs,
        feature_snapshot_refs=feature_snapshot_refs, inventory_refs=inventory_refs,
        capacity_refs=capacity_refs, risk_refs=risk_refs, driver_refs=driver_refs,
        historical_performance=historical_performance, similar_periods=similar_periods,
        previous_decisions=previous_decisions, constraints=constraints, policy_refs=policy_refs,
        data_quality=data_quality, provenance_ids=provenance_ids, created_at=created,
    )
