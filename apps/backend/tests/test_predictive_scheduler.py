from datetime import datetime, time, timezone

import pytest

from src.intelligence.predictive_scheduler import (
    PredictionScheduleEntry, due_predictions, run_due_predictions,
)


def entry(outlet="out1", window="DINNER"):
    return PredictionScheduleEntry(outlet, window, "Asia/Kolkata", time(17, 0))


def test_due_at_local_time_and_repeat_key_suppression() -> None:
    now = datetime(2026, 1, 7, 11, 32, tzinfo=timezone.utc)  # 17:02 IST
    due = due_predictions(now_utc=now, entries=(entry(),), tolerance_minutes=5)
    assert len(due) == 1 and due[0].prediction_as_of == datetime(2026, 1, 7, 11, 30, tzinfo=timezone.utc)
    assert due_predictions(now_utc=now, entries=(entry(),), completed_run_keys=(due[0].run_key,)) == ()


def test_before_and_after_tolerance_not_due() -> None:
    assert due_predictions(now_utc=datetime(2026, 1, 7, 11, 29, tzinfo=timezone.utc), entries=(entry(),)) == ()
    assert due_predictions(now_utc=datetime(2026, 1, 7, 11, 36, tzinfo=timezone.utc), entries=(entry(),)) == ()


def test_timezone_and_duplicate_validation() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        due_predictions(now_utc=datetime(2026, 1, 7), entries=(entry(),))
    with pytest.raises(ValueError, match="unique"):
        due_predictions(now_utc=datetime.now(timezone.utc), entries=(entry(), entry()))
    with pytest.raises(Exception):
        due_predictions(now_utc=datetime.now(timezone.utc), entries=(PredictionScheduleEntry("o", "w", "Invalid/Zone", time()),))


@pytest.mark.asyncio
async def test_callback_execution_order_and_failure_boundary() -> None:
    called = []
    async def callback(item): called.append(item.run_key)
    now = datetime(2026, 1, 7, 11, 30, tzinfo=timezone.utc)
    due = due_predictions(now_utc=now, entries=(entry("b"), entry("a")))
    completed = await run_due_predictions(due=due, callback=callback)
    assert completed == tuple(called) == tuple(sorted(called))
