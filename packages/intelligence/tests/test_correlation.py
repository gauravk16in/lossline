"""Tests for the OPERATIONAL_OVERLOAD_V1 correlation rule."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lossline_intelligence.correlation.engine import correlate_signals
from lossline_intelligence.correlation.rules import CORRELATION_RULE_ID, CORRELATION_RULE_VERSION
from lossline_intelligence.models.incident import IncidentType, ProbableCauseCategory
from lossline_intelligence.models.signal import Signal, SignalType

_W_START = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
_W_END = _W_START + timedelta(minutes=30)


def _signal(
    signal_type: SignalType,
    outlet_id: str = "store_test",
    *,
    signal_id: str | None = None,
    evidence: tuple[str, ...] = ("evt_001",),
    window_start: datetime = _W_START,
    window_end: datetime = _W_END,
) -> Signal:
    sid = signal_id or f"sig_{signal_type}_{outlet_id}"
    return Signal.model_validate(
        {
            "signal_id": sid,
            "outlet_id": outlet_id,
            "signal_type": signal_type,
            "severity": 0.75,
            "current_value": Decimal("10"),
            "baseline_value": Decimal("5"),
            "deviation_ratio": Decimal("1"),
            "unit": "unit",
            "window_start": window_start,
            "window_end": window_end,
            "evidence_event_ids": evidence,
            "detector_version": "test_v1",
        }
    )


def _required_only() -> list[Signal]:
    return [
        _signal(SignalType.ORDER_VOLUME_SPIKE, evidence=("o1",)),
        _signal(SignalType.PREP_TIME_SPIKE, evidence=("p1",)),
        _signal(SignalType.CANCELLATION_SPIKE, evidence=("c1",)),
    ]


def test_all_required_signals_produce_candidate() -> None:
    result = correlate_signals(_required_only())
    assert result is not None
    assert result.incident_type is IncidentType.OPERATIONAL_OVERLOAD
    assert result.outlet_id == "store_test"
    assert result.probable_cause_category is ProbableCauseCategory.OPERATIONAL_CAPACITY_MISMATCH
    assert result.correlation_rule_id == CORRELATION_RULE_ID
    assert result.correlation_rule_version == CORRELATION_RULE_VERSION
    assert len(result.required_signals) == 3


@pytest.mark.parametrize(
    "missing",
    [
        SignalType.ORDER_VOLUME_SPIKE,
        SignalType.PREP_TIME_SPIKE,
        SignalType.CANCELLATION_SPIKE,
    ],
)
def test_missing_one_required_returns_none(missing: SignalType) -> None:
    signals = [s for s in _required_only() if s.signal_type != missing]
    assert correlate_signals(signals) is None


def test_supporting_signals_optional() -> None:
    assert correlate_signals(_required_only()) is not None


def test_supporting_signals_preserved() -> None:
    signals = _required_only() + [
        _signal(SignalType.HANDOFF_DELAY_SPIKE, evidence=("h1",)),
        _signal(SignalType.DELAY_REVIEW_SPIKE, evidence=("d1",)),
    ]
    result = correlate_signals(signals)
    assert result is not None
    assert len(result.supporting_signals) == 2
    assert {s.signal_type for s in result.supporting_signals} == {
        SignalType.HANDOFF_DELAY_SPIKE,
        SignalType.DELAY_REVIEW_SPIKE,
    }


def test_cross_outlet_signals_never_correlate() -> None:
    signals = [
        _signal(SignalType.ORDER_VOLUME_SPIKE, "store_A"),
        _signal(SignalType.PREP_TIME_SPIKE, "store_B"),
        _signal(SignalType.CANCELLATION_SPIKE, "store_A"),
    ]
    assert correlate_signals(signals) is None


def test_temporally_distant_signals_never_correlate() -> None:
    stale_start = _W_START - timedelta(hours=2)
    stale_end = stale_start + timedelta(minutes=30)
    signals = [
        _signal(
            SignalType.ORDER_VOLUME_SPIKE,
            window_start=stale_start,
            window_end=stale_end,
        ),
        _signal(SignalType.PREP_TIME_SPIKE),
        _signal(SignalType.CANCELLATION_SPIKE),
    ]
    assert correlate_signals(signals) is None


def test_deterministic_candidate_id() -> None:
    r1 = correlate_signals(_required_only())
    r2 = correlate_signals(_required_only())
    assert r1 is not None and r2 is not None
    assert r1.candidate_id == r2.candidate_id
    assert "store_test" in r1.candidate_id
    assert CORRELATION_RULE_VERSION in r1.candidate_id


def test_evidence_ids_union_correctly() -> None:
    signals = _required_only() + [
        _signal(SignalType.HANDOFF_DELAY_SPIKE, evidence=("h1", "shared")),
        _signal(SignalType.DELAY_REVIEW_SPIKE, evidence=("d1",)),
    ]
    # add duplicate evidence across required set
    signals[0] = _signal(SignalType.ORDER_VOLUME_SPIKE, evidence=("o1", "shared"))
    result = correlate_signals(signals)
    assert result is not None
    assert set(result.evidence_event_ids) == {"o1", "p1", "c1", "h1", "shared", "d1"}


def test_duplicate_input_signals_do_not_distort_result() -> None:
    base = _required_only()
    dup = base + [
        _signal(
            SignalType.ORDER_VOLUME_SPIKE,
            signal_id=base[0].signal_id,
            evidence=("o1",),
        )
    ]
    r1 = correlate_signals(base)
    r2 = correlate_signals(dup)
    assert r1 == r2


def test_empty_signals_returns_none() -> None:
    assert correlate_signals([]) is None
