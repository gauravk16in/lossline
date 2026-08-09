"""C19 timezone-aware named-window prediction scheduling primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class PredictionScheduleEntry:
    outlet_id: str
    service_window: str
    timezone_name: str
    local_prediction_time: time


@dataclass(frozen=True)
class DuePrediction:
    run_key: str
    outlet_id: str
    service_window: str
    prediction_as_of: datetime


def due_predictions(
    *, now_utc: datetime, entries: tuple[PredictionScheduleEntry, ...],
    completed_run_keys: tuple[str, ...] = (), tolerance_minutes: int = 5,
) -> tuple[DuePrediction, ...]:
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc must be timezone-aware")
    if tolerance_minutes < 0: raise ValueError("tolerance_minutes must be non-negative")
    completed = set(completed_run_keys); due: list[DuePrediction] = []
    identities: set[tuple[str, str]] = set()
    for entry in entries:
        identity = (entry.outlet_id, entry.service_window)
        if identity in identities: raise ValueError("schedule outlet/window entries must be unique")
        identities.add(identity)
        if not entry.outlet_id.strip() or not entry.service_window.strip():
            raise ValueError("schedule identifiers must be non-empty")
        local = now_utc.astimezone(ZoneInfo(entry.timezone_name))
        scheduled = datetime.combine(local.date(), entry.local_prediction_time, tzinfo=local.tzinfo)
        delta_minutes = (local - scheduled).total_seconds() / 60
        run_key = f"{entry.outlet_id}:{entry.service_window}:{local.date().isoformat()}"
        if 0 <= delta_minutes <= tolerance_minutes and run_key not in completed:
            due.append(DuePrediction(run_key, entry.outlet_id, entry.service_window,
                scheduled.astimezone(timezone.utc)))
    return tuple(sorted(due, key=lambda item: item.run_key))


async def run_due_predictions(
    *, due: tuple[DuePrediction, ...], callback: Callable[[DuePrediction], Awaitable[None]],
) -> tuple[str, ...]:
    completed: list[str] = []
    for item in due:
        await callback(item)
        completed.append(item.run_key)
    return tuple(completed)
