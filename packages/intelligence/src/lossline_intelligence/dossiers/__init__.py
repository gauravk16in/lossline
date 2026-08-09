"""Immutable forecast dossier assembly."""

from lossline_intelligence.dossiers.engine import DOSSIER_VERSION, build_forecast_dossier
from lossline_intelligence.dossiers.models import (
    ArtifactRef,
    ConstraintSummary,
    CuratedSummary,
    DataQualitySummary,
    ForecastDossier,
    HistoricalPerformanceSummary,
)

__all__ = [
    "DOSSIER_VERSION", "ArtifactRef", "ConstraintSummary", "CuratedSummary",
    "DataQualitySummary", "ForecastDossier", "HistoricalPerformanceSummary",
    "build_forecast_dossier",
]
