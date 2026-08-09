"""Event-time analysis window helpers (CONFIG_DEFAULT A3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.config import settings


def analysis_window(
    occurred_at: datetime,
    *,
    window_minutes: int | None = None,
) -> tuple[datetime, datetime]:
    """Return the half-open [start, end) window containing ``occurred_at``.

    Windows are aligned to UTC epoch multiples of ``window_minutes``
    (default 30). Slide stepping is reserved for future continuous
    recompute; M0/M1 recompute the containing window on each event.
    """
    minutes = window_minutes if window_minutes is not None else settings.WINDOW_MINUTES
    if minutes <= 0:
        raise ValueError("window_minutes must be positive")

    ts = occurred_at
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    ts = ts.astimezone(timezone.utc)

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    total_minutes = int((ts - epoch).total_seconds() // 60)
    aligned = total_minutes - (total_minutes % minutes)
    start = epoch + timedelta(minutes=aligned)
    end = start + timedelta(minutes=minutes)
    return start, end


def prior_windows(
    window_start: datetime,
    *,
    count: int,
    window_minutes: int | None = None,
) -> list[tuple[datetime, datetime]]:
    """Return ``count`` windows immediately before ``window_start`` (oldest first)."""
    minutes = window_minutes if window_minutes is not None else settings.WINDOW_MINUTES
    result: list[tuple[datetime, datetime]] = []
    cursor = window_start
    for _ in range(count):
        end = cursor
        start = end - timedelta(minutes=minutes)
        result.append((start, end))
        cursor = start
    result.reverse()
    return result
