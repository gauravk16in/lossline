"""Feature semantics, snapshots and pipeline for leakage-safe forecasting."""

from lossline_intelligence.features.catalog import (
    DEMO_FEATURE_DEFINITIONS,
    DEMO_REGISTRY_VERSION,
    build_demo_registry,
)
from lossline_intelligence.features.pipeline import (
    SkuFeatureInput,
    WindowFeatureInput,
    build_dataset,
    build_snapshot,
)
from lossline_intelligence.features.registry import (
    FeatureAvailability,
    FeatureDataType,
    FeatureDefinition,
    FeatureRegistry,
    FeatureRegistryError,
    FeatureTimeSemantics,
    MissingValueStrategy,
)
from lossline_intelligence.features.snapshot import (
    PIPELINE_VERSION,
    DatasetRow,
    FeatureSnapshot,
    SnapshotQuality,
    compute_dataset_fingerprint,
    compute_fingerprint,
    compute_snapshot_id,
)
from lossline_intelligence.features.windows import (
    DINNER_WINDOW,
    LUNCH_WINDOW,
    ServiceWindowConfig,
)

__all__ = [
    "DEMO_FEATURE_DEFINITIONS",
    "DEMO_REGISTRY_VERSION",
    "DINNER_WINDOW",
    "DatasetRow",
    "FeatureAvailability",
    "FeatureDataType",
    "FeatureDefinition",
    "FeatureRegistry",
    "FeatureRegistryError",
    "FeatureSnapshot",
    "FeatureTimeSemantics",
    "LUNCH_WINDOW",
    "MissingValueStrategy",
    "PIPELINE_VERSION",
    "ServiceWindowConfig",
    "SkuFeatureInput",
    "SnapshotQuality",
    "WindowFeatureInput",
    "build_dataset",
    "build_demo_registry",
    "build_snapshot",
    "compute_dataset_fingerprint",
    "compute_fingerprint",
    "compute_snapshot_id",
]
