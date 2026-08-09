"""Backend adapter that orchestrates the pure lossline-intelligence package."""

from src.intelligence.pipeline import run_detection_pipeline

__all__ = ["run_detection_pipeline"]
