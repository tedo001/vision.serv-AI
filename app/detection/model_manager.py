"""Bridges configuration to a ready-to-use detector.

A thin factory the application (and, in Phase 8, the detection engine) uses to
turn the user's selected model + thresholds into a ``YoloDetector``. Keeping
this in one place means the "which model, what thresholds" decision is made
from config/state and nowhere else.
"""

from __future__ import annotations

from app.config.settings import AppConfig
from app.detection.model_catalog import MODELS, ModelInfo
from app.detection.yolo_detector import YoloDetector


def available_models() -> tuple[ModelInfo, ...]:
    """All selectable models, in catalog order."""
    return tuple(MODELS.values())


def build_detector(config: AppConfig) -> YoloDetector:
    """Construct (but do not load) a detector from the active config.

    The caller invokes :meth:`YoloDetector.load` when ready, since loading may
    download weights and allocate GPU memory.
    """
    det = config.detection
    return YoloDetector(
        det.active_model,
        confidence=det.confidence,
        iou=det.iou,
        device=det.device,
        model_dir=det.model_dir,
    )
