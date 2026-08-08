"""Tests for the outcome classifier."""

import pytest

from lossline_intelligence.pipelines.outcome import (
    MIN_ELIGIBLE_ORDERS,
    OutcomeClassification,
    WindowMetrics,
    classify_outcome,
)


def _pre(cancel_rate: float = 0.18, prep_seconds: float = 420.0, orders: int = 20) -> WindowMetrics:
    return WindowMetrics(cancel_rate=cancel_rate, prep_mean_seconds=prep_seconds, order_count=orders)


def _post(cancel_rate: float, prep_seconds: float = 420.0, orders: int = 20) -> WindowMetrics:
    return WindowMetrics(cancel_rate=cancel_rate, prep_mean_seconds=prep_seconds, order_count=orders)


def test_improved_outcome() -> None:
    """Cancel rate fell > 20 %, prep time unchanged → IMPROVED."""
    pre = _pre(cancel_rate=0.18, prep_seconds=400.0)
    post = _post(cancel_rate=0.10, prep_seconds=410.0)  # cancel fell ~44%
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.IMPROVED


def test_worsened_outcome_on_cancel() -> None:
    """Cancel rate worsened >= 15 % → WORSENED."""
    pre = _pre(cancel_rate=0.10)
    post = _post(cancel_rate=0.12)  # 20 % relative worsening
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.WORSENED


def test_worsened_outcome_on_prep() -> None:
    """Prep time worsened >= 15 % → WORSENED."""
    pre = _pre(cancel_rate=0.07, prep_seconds=300.0)
    post = _post(cancel_rate=0.07, prep_seconds=360.0)  # 20 % worsening
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.WORSENED


def test_no_change_outcome() -> None:
    """Small movements in both metrics → NO_CHANGE."""
    pre = _pre(cancel_rate=0.12, prep_seconds=300.0)
    post = _post(cancel_rate=0.13, prep_seconds=305.0)  # < 15 % change
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.NO_CHANGE


def test_insufficient_data_pre() -> None:
    """Pre-window order count below minimum → INSUFFICIENT_DATA."""
    pre = _pre(orders=MIN_ELIGIBLE_ORDERS - 1)
    post = _post(cancel_rate=0.07, orders=20)
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.INSUFFICIENT_DATA


def test_insufficient_data_post() -> None:
    """Post-window order count below minimum → INSUFFICIENT_DATA."""
    pre = _pre(orders=20)
    post = _post(cancel_rate=0.07, orders=MIN_ELIGIBLE_ORDERS - 1)
    result = classify_outcome(pre, post)
    assert result.classification is OutcomeClassification.INSUFFICIENT_DATA


def test_delta_values_are_deterministic() -> None:
    pre = _pre(cancel_rate=0.18)
    post = _post(cancel_rate=0.10)
    r1 = classify_outcome(pre, post)
    r2 = classify_outcome(pre, post)
    assert r1 == r2
    assert r1.cancel_rate_delta == r2.cancel_rate_delta
