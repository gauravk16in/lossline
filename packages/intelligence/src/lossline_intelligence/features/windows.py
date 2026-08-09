"""Named service window configuration and UTC resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import zoneinfo


@dataclass(frozen=True)
class ServiceWindowConfig:
    """One named service window definition for an outlet.

    Windows are half-open ``[start, end)`` in the outlet's local timezone.
    ``resolve_utc`` converts a local date to UTC boundaries.
    """

    window_name: str
    start_local: time
    end_local: time
    timezone_name: str

    def __post_init__(self) -> None:
        if not self.window_name.strip():
            raise ValueError("window_name must be non-empty")
        if not self.timezone_name.strip():
            raise ValueError("timezone_name must be non-empty")
        try:
            zoneinfo.ZoneInfo(self.timezone_name)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid timezone: {self.timezone_name}") from exc
        if self.start_local >= self.end_local:
            raise ValueError("start_local must be before end_local")

    def resolve_utc(self, window_date: date) -> tuple[datetime, datetime]:
        """Resolve half-open ``[start, end)`` UTC for a given local date."""
        tz = zoneinfo.ZoneInfo(self.timezone_name)
        start_local = datetime.combine(window_date, self.start_local, tzinfo=tz)
        end_local = datetime.combine(window_date, self.end_local, tzinfo=tz)
        return (
            start_local.astimezone(timezone.utc),
            end_local.astimezone(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Demo windows matching C03 golden scenarios
# ---------------------------------------------------------------------------

DINNER_WINDOW = ServiceWindowConfig(
    window_name="DINNER",
    start_local=time(18, 30),
    end_local=time(21, 30),
    timezone_name="Asia/Kolkata",
)

LUNCH_WINDOW = ServiceWindowConfig(
    window_name="LUNCH",
    start_local=time(11, 30),
    end_local=time(14, 30),
    timezone_name="Asia/Kolkata",
)
