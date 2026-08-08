"""Deterministic historical baseline calculator.

Responsibility
--------------
Given a sequence of historical MetricSnapshots for ONE outlet, compute
a stable BaselineResult for each metric of interest.

Algorithm (CONFIG_DEFAULT A4 from FINAL_IMPLEMENTATION_PLAN.md):
  For each metric:
    1. Collect the non-zero values from the historical snapshots.
    2. Compute the median as the baseline central value.
    3. If enough samples exist, compute the MAD (median absolute deviation)
       as a dispersion estimate.
    4. Attach a quality flag indicating whether the history is sufficient.

What this module does NOT do
-----------------------------
- No anomaly detection, no signals, no correlation, no LLM.
- No I/O, no database, no Redis.
- No side effects of any kind.

Configuration
-------------
All tuneable numbers are exposed as module-level CONFIG_DEFAULT constants so
callers can override them via versioned configuration without touching logic.

  MIN_HISTORY_WINDOWS : int
      Minimum number of historical snapshots required for the baseline to be
      marked as ``sufficient``.  Below this count the median is still computed
      if any samples exist, but ``sufficient_history`` is set to False.
      CONFIG_DEFAULT: 4  (from FINAL_IMPLEMENTATION_PLAN.md §Aggregation A4)

  DECIMAL_PLACES : Decimal
      Rounding precision for all Decimal outputs.
      CONFIG_DEFAULT: 4 decimal places.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from lossline_intelligence.aggregation.metric_snapshot import MetricSnapshot


# ---------------------------------------------------------------------------
# Configuration defaults (CONFIG_DEFAULT — not business facts)
# ---------------------------------------------------------------------------

#: Minimum number of historical windows for baseline to be considered sufficient.
#: From FINAL_IMPLEMENTATION_PLAN.md §Aggregation A4.
MIN_HISTORY_WINDOWS: int = 4

#: Decimal rounding precision for all output fields.
DECIMAL_PLACES: Decimal = Decimal("0.0001")

#: Version string embedded in every BaselineResult for traceability.
BASELINE_VERSION: str = "baseline.v1"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricBaseline:
    """Baseline statistics for a single metric dimension.

    Attributes
    ----------
    median:
        Median value across historical windows.  ``None`` when no historical
        samples exist for this metric (sparse-data safe).
    mad:
        Median absolute deviation — a robust dispersion estimate.
        ``None`` when fewer than 2 non-None samples exist.
    sample_count:
        Number of historical windows that contributed a non-None value for
        this metric.
    """

    median: Decimal | None
    mad: Decimal | None
    sample_count: int


@dataclass(frozen=True)
class BaselineResult:
    """Complete baseline for one outlet derived from historical MetricSnapshots.

    All metric fields follow the same structure as MetricSnapshot so that
    detectors can directly compare current vs. baseline values without
    field-name translation.

    Attributes
    ----------
    outlet_id:
        The outlet this baseline is for.
    sample_count:
        Total number of historical snapshots used (may be 0).
    sufficient_history:
        True iff sample_count >= MIN_HISTORY_WINDOWS.  Detectors SHOULD
        abstain or reduce confidence when this is False.
    baseline_version:
        Version string for traceability and cache invalidation.
    order_count:
        Baseline for window order count (integer orders per window).
    cancellation_rate:
        Baseline cancellation rate in [0, 1].
    avg_prep_minutes:
        Baseline mean preparation time in minutes.
    p90_prep_minutes:
        Baseline p90 preparation time in minutes.
    avg_handoff_wait_minutes:
        Baseline mean handoff wait in minutes.
    negative_review_rate:
        Baseline proportion of reviews that are negative (negative / total).
        None when no review samples exist.
    delay_review_rate:
        Baseline proportion of reviews that mention delay keywords.
        None when no review samples exist.
    """

    outlet_id: str
    sample_count: int
    sufficient_history: bool
    baseline_version: str

    order_count: MetricBaseline
    cancellation_rate: MetricBaseline
    avg_prep_minutes: MetricBaseline
    p90_prep_minutes: MetricBaseline
    avg_handoff_wait_minutes: MetricBaseline
    negative_review_rate: MetricBaseline
    delay_review_rate: MetricBaseline


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_dec(value: float | int) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _median_dec(values: list[Decimal]) -> Decimal | None:
    """Return the median of a non-empty list of Decimals, or None if empty."""
    if not values:
        return None
    # statistics.median works on Decimal natively
    return Decimal(str(statistics.median(values))).quantize(
        DECIMAL_PLACES, rounding=ROUND_HALF_UP
    )


def _mad_dec(values: list[Decimal], med: Decimal) -> Decimal | None:
    """Return the MAD (median absolute deviation) for a list of Decimals.

    Returns None when fewer than 2 values exist (MAD is not meaningful for
    a single sample).  Returns Decimal("0.0000") when all values are identical.
    """
    if len(values) < 2:
        return None
    abs_devs = [abs(v - med) for v in values]
    return Decimal(str(statistics.median(abs_devs))).quantize(
        DECIMAL_PLACES, rounding=ROUND_HALF_UP
    )


def _metric_baseline(values: list[Decimal]) -> MetricBaseline:
    """Build a MetricBaseline from a (possibly empty) list of Decimal samples."""
    med = _median_dec(values)
    mad = _mad_dec(values, med) if med is not None else None
    return MetricBaseline(median=med, mad=mad, sample_count=len(values))


def _review_rate(
    numerator_values: list[int],
    denominator_values: list[int],
) -> MetricBaseline:
    """Build a rate-based MetricBaseline (e.g. negative_review / review_count).

    Parameters
    ----------
    numerator_values:
        Per-window numerator counts (e.g. negative_review_count).
    denominator_values:
        Per-window denominator counts (e.g. review_count).
        Paired 1:1 with numerator_values.

    Only windows where the denominator > 0 contribute a sample.
    """
    rates: list[Decimal] = []
    for num, den in zip(numerator_values, denominator_values):
        if den > 0:
            rates.append(_to_dec(num / den))
    return _metric_baseline(rates)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_baseline(
    historical_snapshots: Sequence[MetricSnapshot],
    *,
    outlet_id: str,
    min_history_windows: int = MIN_HISTORY_WINDOWS,
) -> BaselineResult:
    """Compute a deterministic baseline from historical MetricSnapshots.

    Only snapshots whose ``outlet_id`` matches the requested ``outlet_id`` are
    used.  Snapshots for other outlets are silently ignored so callers can
    safely pass a mixed sequence.

    The baseline algorithm is:
      - Collect per-metric values from all matching snapshots.
      - Compute the median as the central value.
      - Compute the MAD as the dispersion estimate (None if < 2 samples).
      - Mark ``sufficient_history = sample_count >= min_history_windows``.

    Sparse cases:
      - Zero historical snapshots → all MetricBaseline fields are None / 0.
      - One snapshot → median is set; MAD is None (not meaningful).
      - Metric absent from some snapshots (e.g. zero prep events) → those
        windows contribute ``Decimal("0")`` — zeros ARE included in the
        median so sparse windows pull the baseline toward zero, which is the
        conservative safe choice for the detector layer.

    Parameters
    ----------
    historical_snapshots:
        Sequence of historical MetricSnapshot objects.  Order does not matter.
        May be empty.
    outlet_id:
        The outlet to compute the baseline for.  Must be non-empty.
    min_history_windows:
        Override for the minimum-history threshold.  Defaults to the
        module-level CONFIG_DEFAULT (4).

    Returns
    -------
    BaselineResult
        A fully populated, immutable baseline.  Never raises on sparse data.

    Raises
    ------
    ValueError
        If ``outlet_id`` is empty or whitespace-only.
    """
    if not outlet_id or not outlet_id.strip():
        raise ValueError("outlet_id must be a non-empty string")

    # Filter to this outlet only — never use another outlet's history.
    own: list[MetricSnapshot] = [
        s for s in historical_snapshots if s.outlet_id == outlet_id
    ]

    n = len(own)
    sufficient = n >= min_history_windows

    if n == 0:
        # No history at all — return a zero-sample baseline with all None medians.
        empty = MetricBaseline(median=None, mad=None, sample_count=0)
        return BaselineResult(
            outlet_id=outlet_id,
            sample_count=0,
            sufficient_history=False,
            baseline_version=BASELINE_VERSION,
            order_count=empty,
            cancellation_rate=empty,
            avg_prep_minutes=empty,
            p90_prep_minutes=empty,
            avg_handoff_wait_minutes=empty,
            negative_review_rate=empty,
            delay_review_rate=empty,
        )

    # --- Collect per-metric sample lists -------------------------------------
    order_counts         = [_to_dec(s.order_count)               for s in own]
    cancel_rates         = [s.cancellation_rate                   for s in own]
    avg_preps            = [s.avg_prep_minutes                    for s in own]
    p90_preps            = [s.p90_prep_minutes                    for s in own]
    avg_handoffs         = [s.avg_handoff_wait_minutes            for s in own]
    neg_review_nums      = [s.negative_review_count               for s in own]
    delay_review_nums    = [s.delay_review_count                  for s in own]
    review_dens          = [s.review_count                        for s in own]

    return BaselineResult(
        outlet_id=outlet_id,
        sample_count=n,
        sufficient_history=sufficient,
        baseline_version=BASELINE_VERSION,
        order_count=_metric_baseline(order_counts),
        cancellation_rate=_metric_baseline(cancel_rates),
        avg_prep_minutes=_metric_baseline(avg_preps),
        p90_prep_minutes=_metric_baseline(p90_preps),
        avg_handoff_wait_minutes=_metric_baseline(avg_handoffs),
        negative_review_rate=_review_rate(neg_review_nums, review_dens),
        delay_review_rate=_review_rate(delay_review_nums, review_dens),
    )
