"""Signal registry and point-in-time forecast-safety enforcement."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Annotated, Mapping

from pydantic import StringConstraints

from lossline_intelligence.signals.models import (
    EntityType,
    NormalizedSignal,
    SignalCategory,
)


Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ValueKind(StrEnum):
    DECIMAL = "DECIMAL"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    CATEGORICAL = "CATEGORICAL"
    TIMESTAMP = "TIMESTAMP"
    JSON = "JSON"


@dataclass(frozen=True)
class SignalDefinition:
    signal_type: Identifier
    version: Identifier
    category: SignalCategory
    entity_type: EntityType
    value_kind: ValueKind
    unit: Identifier
    forecast_safe: bool
    max_staleness: timedelta
    leakage_rationale: str
    allowed_sources: tuple[Identifier, ...]

    def __post_init__(self) -> None:
        for name in ("signal_type", "version", "unit", "leakage_rationale"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.max_staleness < timedelta(0):
            raise ValueError("max_staleness cannot be negative")
        if not self.allowed_sources or len(self.allowed_sources) != len(set(self.allowed_sources)):
            raise ValueError("allowed_sources must be non-empty and unique")


class RegistryError(ValueError):
    """The signal is unknown or violates its registered semantic contract."""


class ForecastSafetyError(ValueError):
    """The signal was unavailable, unsafe, or stale at prediction time."""


class SignalRegistry:
    def __init__(
        self,
        definitions: tuple[SignalDefinition, ...],
        *,
        registry_version: Identifier = "signal_registry.v1",
    ) -> None:
        if not str(registry_version).strip():
            raise RegistryError("registry_version must be non-empty")
        entries: dict[str, SignalDefinition] = {}
        for definition in definitions:
            if definition.signal_type in entries:
                raise RegistryError(f"duplicate signal type: {definition.signal_type}")
            entries[definition.signal_type] = definition
        if not entries:
            raise RegistryError("signal registry cannot be empty")
        self._registry_version = str(registry_version).strip()
        self._entries: Mapping[str, SignalDefinition] = MappingProxyType(entries)

    @property
    def registry_version(self) -> str:
        return self._registry_version

    @property
    def definitions(self) -> tuple[SignalDefinition, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    @property
    def fingerprint(self) -> str:
        payload = [
            {
                "signal_type": item.signal_type,
                "version": item.version,
                "category": item.category.value,
                "entity_type": item.entity_type.value,
                "value_kind": item.value_kind.value,
                "unit": item.unit,
                "forecast_safe": item.forecast_safe,
                "max_staleness_seconds": item.max_staleness.total_seconds(),
                "leakage_rationale": item.leakage_rationale,
                "allowed_sources": sorted(item.allowed_sources),
            }
            for item in self.definitions
        ]
        encoded = json.dumps(
            {"registry_version": self.registry_version, "signals": payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def definition_for(self, signal_type: str) -> SignalDefinition:
        try:
            return self._entries[signal_type]
        except KeyError as exc:
            raise RegistryError(f"unregistered signal type: {signal_type}") from exc

    def validate(self, signal: NormalizedSignal) -> SignalDefinition:
        definition = self.definition_for(signal.signal_type)
        mismatches = {
            "category": (signal.category, definition.category),
            "entity_type": (signal.entity_type, definition.entity_type),
            "value_kind": (signal.value.kind, definition.value_kind),
            "unit": (signal.unit, definition.unit),
        }
        for field, (actual, expected) in mismatches.items():
            if actual != expected:
                raise RegistryError(
                    f"{signal.signal_type} {field} must be {expected}, got {actual}"
                )
        if signal.source not in definition.allowed_sources:
            raise RegistryError(f"source {signal.source} is not allowed for {signal.signal_type}")
        return definition

    def require_forecast_safe(
        self, signal: NormalizedSignal, *, prediction_as_of: datetime
    ) -> SignalDefinition:
        if prediction_as_of.tzinfo is None or prediction_as_of.utcoffset() is None:
            raise ForecastSafetyError("prediction_as_of must include a UTC offset")
        as_of = prediction_as_of.astimezone(timezone.utc)
        definition = self.validate(signal)
        if not definition.forecast_safe:
            raise ForecastSafetyError(f"{signal.signal_type} is not forecast-safe")
        if signal.observed_at > as_of:
            raise ForecastSafetyError("signal was not observed by prediction_as_of")
        if signal.provenance.ingested_at > as_of:
            raise ForecastSafetyError("signal was not ingested by prediction_as_of")
        if as_of - signal.observed_at > definition.max_staleness:
            raise ForecastSafetyError("signal exceeds its maximum staleness")
        return definition
