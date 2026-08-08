"""Backward-compatible re-export — canonical implementation is in correlation/."""

from lossline_intelligence.correlation.engine import correlate_signals as correlate_overload

__all__ = ["correlate_overload"]
