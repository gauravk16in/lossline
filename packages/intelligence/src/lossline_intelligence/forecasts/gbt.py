"""Gradient-boosted tabular demand forecast model (C06).

This module implements the first ML forecast model using LightGBM. It owns:
- ``MLForecastArtifact`` — versioned, immutable model artifact with training
  metadata, evaluation metrics and residual-bound parameters.
- ``GBTForecast`` — Pydantic serialization boundary for one per-grain forecast.
- ``GBTAbstention`` — explicit abstention when no trained artifact is available.
- ``train_gbt_model()`` — rolling-origin chronological training and evaluation.
- ``forecast_gbt()`` — single-snapshot inference against a loaded artifact.

Architecture constraints (C01):
- No LLM calls, no DB/Redis access, no process-global mutable state.
- All metric arithmetic uses ``Decimal``; never ``float`` in outputs.
- Bounds are labelled ``empirical_residual_80.v1``; not calibrated probabilities.
- The booster seed is fixed; artifact IDs are deterministic for identical inputs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from hashlib import sha256
from math import sqrt
from typing import Annotated, Any, Sequence

import lightgbm as lgb
import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from lossline_intelligence.features.snapshot import (
    DatasetRow,
    FeatureSnapshot,
    compute_dataset_fingerprint,
)


# ---------------------------------------------------------------------------
# Module-level constants — never hardcoded in logic
# ---------------------------------------------------------------------------

GBT_VERSION: str = "lightgbm_gbt.v1"
GBT_INTERVAL_METHOD: str = "empirical_residual_80.v1"
MIN_TRAIN_ROWS: int = 20

# Default test fraction for rolling-origin split (last fraction of rows by time)
DEFAULT_TEST_FRACTION: float = 0.20

# Pinned hyperparameters — callers may pass overrides as keyword arguments
DEFAULT_PARAMS: dict[str, Any] = {
    "objective": "regression_l1",
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "seed": 42,
    "verbose": -1,
}

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_DP = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class GBTAbstentionReason(StrEnum):
    NO_ARTIFACT = "NO_ARTIFACT"
    INVALID_TARGET_SNAPSHOT = "INVALID_TARGET_SNAPSHOT"


# ---------------------------------------------------------------------------
# Domain objects (internal — dataclass, no Pydantic overhead)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MLForecastArtifact:
    """Versioned, immutable model artifact produced by ``train_gbt_model``.

    ``artifact_id`` is a deterministic SHA-256 of training provenance; the
    internal LightGBM booster is excluded from that computation.
    """

    artifact_id: str
    model_version: str
    training_cutoff: datetime          # max(window_end) in training rows, UTC
    dataset_fingerprint: str
    registry_fingerprint: str
    code_version: str
    params: dict[str, Any]
    params_fingerprint: str
    feature_names: tuple[str, ...]     # sorted, numeric/boolean only
    evaluation_metrics: dict[str, Decimal]  # mae, rmse, wmape, bias on test fold
    residual_p10: Decimal              # 10th pct of signed training-fold residuals
    residual_p90: Decimal              # 90th pct of signed training-fold residuals
    checksum: str                      # SHA-256 of booster string representation
    created_at: datetime
    # Internal booster — excluded from __hash__/__eq__ via compare=False
    _booster: lgb.Booster = field(compare=False, repr=False)


@dataclass(frozen=True)
class GBTAbstention:
    """Explicit abstention when inference cannot proceed."""

    feature_snapshot_id: str
    reason: GBTAbstentionReason
    artifact_id: str | None = None


# ---------------------------------------------------------------------------
# Serialization boundary (Pydantic)
# ---------------------------------------------------------------------------


class GBTForecast(BaseModel):
    """Validated GBT forecast at the canonical predictive grain (C01 contract)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    forecast_id: Identifier
    model_version: Identifier
    artifact_id: Identifier
    interval_method: Identifier
    prediction_as_of: datetime
    outlet_id: Identifier
    sku_id: Identifier
    service_window: Identifier
    window_start: datetime
    window_end: datetime
    feature_snapshot_id: Identifier
    point_demand: Decimal
    lower_demand: Decimal
    upper_demand: Decimal
    data_sufficient: bool

    @field_validator("prediction_as_of", "window_start", "window_end")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value.astimezone(timezone.utc)

    @field_validator("point_demand", "lower_demand", "upper_demand")
    @classmethod
    def validate_demand(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("forecast demand must be finite and non-negative")
        return value.quantize(_DP, rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_bounds(self) -> "GBTForecast":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if not self.lower_demand <= self.point_demand <= self.upper_demand:
            raise ValueError("forecast bounds must contain point_demand")
        return self


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


def _params_fingerprint(params: dict[str, Any]) -> str:
    return sha256(
        json.dumps(params, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _artifact_id(
    training_cutoff: datetime,
    dataset_fingerprint: str,
    registry_fingerprint: str,
    code_version: str,
    params_fp: str,
) -> str:
    payload = json.dumps(
        {
            "code_version": code_version,
            "dataset_fingerprint": dataset_fingerprint,
            "params_fingerprint": params_fp,
            "registry_fingerprint": registry_fingerprint,
            "training_cutoff": training_cutoff.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"art_gbt_{sha256(payload).hexdigest()[:24]}"


def _forecast_id(target: FeatureSnapshot, artifact_id: str) -> str:
    payload = json.dumps(
        {
            "artifact_id": artifact_id,
            "snapshot_id": target.snapshot_id,
            "version": GBT_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"fcst_gbt_{sha256(payload).hexdigest()[:20]}"


def _numeric_feature_names(snapshots: Sequence[FeatureSnapshot]) -> tuple[str, ...]:
    """Sorted feature names that are numeric or boolean across all snapshots.

    String features are excluded — they cannot be used in a tabular regressor
    without encoding, which is not part of the C06 MVP feature set.
    """
    if not snapshots:
        return ()
    candidate_keys = sorted(snapshots[0].feature_values.keys())
    numeric: list[str] = []
    for key in candidate_keys:
        # Accept if every snapshot has a numeric/boolean/None value (not str)
        if all(
            isinstance(snap.feature_values.get(key), (bool, int, Decimal, type(None)))
            for snap in snapshots
        ):
            numeric.append(key)
    return tuple(numeric)


def snapshot_to_feature_vector(
    snapshot: FeatureSnapshot, feature_names: tuple[str, ...]
) -> list[float]:
    """Extract a numeric feature vector in deterministic feature order.

    - ``bool``  → ``float`` (0.0 or 1.0); checked before ``int`` (subclass)
    - ``int``   → ``float``
    - ``Decimal`` → ``float``
    - ``None``  → ``float("nan")``
    String values are skipped (not in ``feature_names`` by construction).
    """
    vector: list[float] = []
    for name in feature_names:
        value = snapshot.feature_values.get(name)
        if isinstance(value, bool):
            vector.append(float(value))
        elif isinstance(value, int):
            vector.append(float(value))
        elif isinstance(value, Decimal):
            vector.append(float(value))
        else:
            # None or missing
            vector.append(float("nan"))
    return vector


def _quantile_decimal(values: Sequence[float], probability: float) -> Decimal:
    """Linear-interpolation quantile over a sequence of floats → Decimal."""
    if not values:
        return Decimal("0")
    arr = sorted(values)
    pos = probability * (len(arr) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(arr) - 1)
    frac = pos - lo
    result = arr[lo] + frac * (arr[hi] - arr[lo])
    return Decimal(str(result)).quantize(_DP, rounding=ROUND_HALF_UP)


def _clamp_non_negative(value: Decimal) -> Decimal:
    return max(value, Decimal("0")).quantize(_DP, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_gbt_model(
    rows: Sequence[DatasetRow],
    *,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    params: dict[str, Any] | None = None,
    min_train_rows: int = MIN_TRAIN_ROWS,
) -> MLForecastArtifact | None:
    """Train a LightGBM tabular regression model with rolling-origin split.

    Returns ``None`` when the uncensored dataset is too small to train.

    Algorithm:
    1. Exclude censored rows from the eligible set.
    2. Sort eligible rows chronologically by ``window_start``.
    3. Enforce ``min_train_rows`` on the training split.
    4. Train set = first ``(1 - test_fraction)`` rows; test set = remainder.
    5. Build feature matrix; train LightGBM booster with pinned params.
    6. Compute training-fold residuals → ``residual_p10`` / ``residual_p90``.
    7. Evaluate on held-out test fold: MAE, RMSE, WMAPE, bias.
    8. Assemble and return ``MLForecastArtifact``.
    """
    effective_params = {**DEFAULT_PARAMS, **(params or {})}

    # 1. Exclude censored rows, sort chronologically
    eligible = sorted(
        [row for row in rows if not row.censored],
        key=lambda r: (r.snapshot.window_start, r.snapshot.outlet_id, r.snapshot.sku_id),
    )

    if not eligible:
        return None

    # 2. Determine feature names from the full eligible set
    feature_names = _numeric_feature_names([r.snapshot for r in eligible])
    if not feature_names:
        return None

    # 3. Split
    n = len(eligible)
    split_idx = max(1, int(n * (1.0 - test_fraction)))
    train_rows = eligible[:split_idx]
    test_rows = eligible[split_idx:]

    if len(train_rows) < min_train_rows:
        return None

    # 4. Build train matrix
    X_train = np.array(
        [snapshot_to_feature_vector(r.snapshot, feature_names) for r in train_rows],
        dtype=np.float64,
    )
    y_train = np.array(
        [float(r.target_demand_quantity) for r in train_rows], dtype=np.float64
    )

    # 5. Train booster
    train_data = lgb.Dataset(X_train, label=y_train, feature_name=list(feature_names))
    booster = lgb.train(
        {k: v for k, v in effective_params.items() if k != "n_estimators"},
        train_data,
        num_boost_round=int(effective_params.get("n_estimators", 300)),
    )

    # 6. Training-fold residuals → empirical interval parameters
    train_preds = booster.predict(X_train)
    train_residuals = [
        float(pred) - float(r.target_demand_quantity)
        for pred, r in zip(train_preds, train_rows)
    ]
    residual_p10 = _quantile_decimal(train_residuals, 0.10)
    residual_p90 = _quantile_decimal(train_residuals, 0.90)

    # 7. Evaluate on test fold
    if test_rows:
        X_test = np.array(
            [snapshot_to_feature_vector(r.snapshot, feature_names) for r in test_rows],
            dtype=np.float64,
        )
        y_test = [float(r.target_demand_quantity) for r in test_rows]
        test_preds = list(booster.predict(X_test))
        errors = [p - a for p, a in zip(test_preds, y_test)]
        absolute = [abs(e) for e in errors]
        count_d = Decimal(len(errors))
        mae = (sum(Decimal(str(a)) for a in absolute) / count_d).quantize(
            _DP, rounding=ROUND_HALF_UP
        )
        mean_sq = sum(e * e for e in errors) / len(errors)
        rmse = Decimal(str(sqrt(mean_sq))).quantize(_DP, rounding=ROUND_HALF_UP)
        total_actual = sum(Decimal(str(a)) for a in y_test)
        wmape = (
            None
            if total_actual == 0
            else (sum(Decimal(str(a)) for a in absolute) / total_actual).quantize(
                _DP, rounding=ROUND_HALF_UP
            )
        )
        bias = (sum(Decimal(str(e)) for e in errors) / count_d).quantize(
            _DP, rounding=ROUND_HALF_UP
        )
        eval_metrics: dict[str, Decimal] = {"mae": mae, "rmse": rmse, "bias": bias}
        if wmape is not None:
            eval_metrics["wmape"] = wmape
    else:
        eval_metrics = {}

    # 8. Artifact provenance
    training_cutoff = max(r.snapshot.window_end for r in train_rows)
    training_cutoff = _utc(training_cutoff)
    registry_fingerprint = train_rows[0].snapshot.registry_fingerprint
    dataset_fp = compute_dataset_fingerprint(tuple(eligible))
    params_fp = _params_fingerprint(effective_params)
    art_id = _artifact_id(
        training_cutoff, dataset_fp, registry_fingerprint, GBT_VERSION, params_fp
    )
    booster_str = booster.model_to_string()
    checksum = sha256(booster_str.encode("utf-8")).hexdigest()

    return MLForecastArtifact(
        artifact_id=art_id,
        model_version=GBT_VERSION,
        training_cutoff=training_cutoff,
        dataset_fingerprint=dataset_fp,
        registry_fingerprint=registry_fingerprint,
        code_version=GBT_VERSION,
        params=effective_params,
        params_fingerprint=params_fp,
        feature_names=feature_names,
        evaluation_metrics=eval_metrics,
        residual_p10=residual_p10,
        residual_p90=residual_p90,
        checksum=checksum,
        created_at=datetime.now(timezone.utc),
        _booster=booster,
    )


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def forecast_gbt(
    target: FeatureSnapshot,
    artifact: MLForecastArtifact | None,
    *,
    prediction_as_of: datetime | None = None,
) -> GBTForecast | GBTAbstention:
    """Produce a demand forecast for *target* using *artifact*.

    Returns ``GBTAbstention`` when:
    - ``artifact`` is ``None``;
    - the target window has already started (temporal safety violation).

    Bounds are constructed by applying the artifact's empirical residual
    percentile offsets to the point prediction, then clamping to ≥ 0 and
    ensuring containment.
    """
    if artifact is None:
        return GBTAbstention(
            feature_snapshot_id=target.snapshot_id,
            reason=GBTAbstentionReason.NO_ARTIFACT,
            artifact_id=None,
        )

    as_of = _utc(prediction_as_of if prediction_as_of is not None else target.prediction_as_of)

    if target.window_start < as_of:
        return GBTAbstention(
            feature_snapshot_id=target.snapshot_id,
            reason=GBTAbstentionReason.INVALID_TARGET_SNAPSHOT,
            artifact_id=artifact.artifact_id,
        )

    # Feature extraction and inference
    x = np.array(
        [snapshot_to_feature_vector(target, artifact.feature_names)], dtype=np.float64
    )
    raw_pred = float(artifact._booster.predict(x)[0])

    # Point demand: clamped to ≥ 0
    point = _clamp_non_negative(Decimal(str(raw_pred)))

    # Empirical actual-demand bounds from residual = prediction - actual:
    # actual = prediction - residual.  The upper residual quantile therefore
    # produces the lower demand bound and the lower quantile the upper bound.
    lower = _clamp_non_negative(
        (Decimal(str(raw_pred)) - artifact.residual_p90).quantize(_DP, rounding=ROUND_HALF_UP)
    )
    upper = _clamp_non_negative(
        (Decimal(str(raw_pred)) - artifact.residual_p10).quantize(_DP, rounding=ROUND_HALF_UP)
    )

    # Ensure containment invariant: lower ≤ point ≤ upper
    lower = min(lower, point)
    upper = max(upper, point)

    return GBTForecast(
        forecast_id=_forecast_id(target, artifact.artifact_id),
        model_version=GBT_VERSION,
        artifact_id=artifact.artifact_id,
        interval_method=GBT_INTERVAL_METHOD,
        prediction_as_of=as_of,
        outlet_id=target.outlet_id,
        sku_id=target.sku_id,
        service_window=target.service_window,
        window_start=target.window_start,
        window_end=target.window_end,
        feature_snapshot_id=target.snapshot_id,
        point_demand=point,
        lower_demand=lower,
        upper_demand=upper,
        data_sufficient=True,
    )
