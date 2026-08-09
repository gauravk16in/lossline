"""Versioned feature definitions for point-in-time forecast construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Annotated, Mapping

from pydantic import StringConstraints

from lossline_intelligence.signals.models import SignalCategory


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FeatureDataType(StrEnum):
    DECIMAL = "DECIMAL"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    CATEGORICAL = "CATEGORICAL"
    TIMESTAMP = "TIMESTAMP"


class FeatureTimeSemantics(StrEnum):
    STATIC = "STATIC"
    OBSERVED = "OBSERVED"
    FORECAST_VINTAGE = "FORECAST_VINTAGE"
    SCHEDULED_FUTURE = "SCHEDULED_FUTURE"
    HISTORICAL_LAG = "HISTORICAL_LAG"
    ROLLING_HISTORY = "ROLLING_HISTORY"


class FeatureAvailability(StrEnum):
    AT_PREDICTION_TIME = "AT_PREDICTION_TIME"
    FUTURE_KNOWN = "FUTURE_KNOWN"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"


class MissingValueStrategy(StrEnum):
    REJECT_ROW = "REJECT_ROW"
    EXPLICIT_MISSING = "EXPLICIT_MISSING"
    IMPUTE_CONSTANT = "IMPUTE_CONSTANT"
    IMPUTE_HISTORICAL = "IMPUTE_HISTORICAL"


@dataclass(frozen=True)
class FeatureDefinition:
    """Semantic contract for one model feature at one version."""

    feature_id: Identifier
    version: Identifier
    source: Identifier
    category: SignalCategory
    data_type: FeatureDataType
    unit: Identifier
    entity_grain: tuple[Identifier, ...]
    time_semantics: FeatureTimeSemantics
    availability: FeatureAvailability
    future_known: bool
    transformation: Identifier
    missing_value_strategy: MissingValueStrategy
    max_staleness: timedelta | None
    leakage_rationale: str

    def __post_init__(self) -> None:
        for name in (
            "feature_id",
            "version",
            "source",
            "unit",
            "transformation",
            "leakage_rationale",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if not self.entity_grain or any(not str(item).strip() for item in self.entity_grain):
            raise ValueError("entity_grain must contain non-empty dimensions")
        if len(self.entity_grain) != len(set(self.entity_grain)):
            raise ValueError("entity_grain dimensions must be unique")
        if self.max_staleness is not None and self.max_staleness < timedelta(0):
            raise ValueError("max_staleness cannot be negative")
        if self.future_known != (self.availability is FeatureAvailability.FUTURE_KNOWN):
            raise ValueError(
                "future_known must be true exactly when availability is FUTURE_KNOWN"
            )
        future_semantics = {
            FeatureTimeSemantics.STATIC,
            FeatureTimeSemantics.FORECAST_VINTAGE,
            FeatureTimeSemantics.SCHEDULED_FUTURE,
        }
        if self.future_known and self.time_semantics not in future_semantics:
            raise ValueError(
                "future-known features require static, forecast-vintage, or scheduled semantics"
            )
        if (
            self.time_semantics is FeatureTimeSemantics.FORECAST_VINTAGE
            and not self.future_known
        ):
            raise ValueError("forecast-vintage features must be future-known")


class FeatureRegistryError(ValueError):
    """A feature definition is missing, duplicated, or internally incompatible."""


class FeatureRegistry:
    """Immutable lookup for one complete, versioned feature contract."""

    def __init__(
        self,
        definitions: tuple[FeatureDefinition, ...],
        *,
        registry_version: Identifier,
    ) -> None:
        if not str(registry_version).strip():
            raise FeatureRegistryError("registry_version must be non-empty")
        entries: dict[str, FeatureDefinition] = {}
        for definition in definitions:
            if definition.feature_id in entries:
                raise FeatureRegistryError(
                    f"duplicate feature_id: {definition.feature_id}"
                )
            entries[definition.feature_id] = definition
        if not entries:
            raise FeatureRegistryError("feature registry cannot be empty")
        self._registry_version = str(registry_version).strip()
        self._entries: Mapping[str, FeatureDefinition] = MappingProxyType(entries)

    @property
    def registry_version(self) -> str:
        return self._registry_version

    @property
    def definitions(self) -> tuple[FeatureDefinition, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    @property
    def fingerprint(self) -> str:
        payload = [
            {
                "feature_id": item.feature_id,
                "version": item.version,
                "source": item.source,
                "category": item.category.value,
                "data_type": item.data_type.value,
                "unit": item.unit,
                "entity_grain": item.entity_grain,
                "time_semantics": item.time_semantics.value,
                "availability": item.availability.value,
                "future_known": item.future_known,
                "transformation": item.transformation,
                "missing_value_strategy": item.missing_value_strategy.value,
                "max_staleness_seconds": (
                    None
                    if item.max_staleness is None
                    else item.max_staleness.total_seconds()
                ),
                "leakage_rationale": item.leakage_rationale,
            }
            for item in self.definitions
        ]
        encoded = json.dumps(
            {"registry_version": self.registry_version, "features": payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def definition_for(self, feature_id: str) -> FeatureDefinition:
        try:
            return self._entries[feature_id]
        except KeyError as exc:
            raise FeatureRegistryError(f"unregistered feature_id: {feature_id}") from exc


