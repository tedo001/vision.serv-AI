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


def build_detector(
    config: AppConfig,
    *,
    model_override: str | None = None,
    device_override: str | None = None,
) -> YoloDetector:
    """Construct (but do not load) a detector from the active config.

    ``model_override`` / ``device_override`` let a caller (e.g. the Video
    Detection tab) try a model or device without changing saved config. The
    caller invokes :meth:`YoloDetector.load` when ready, since loading may
    download weights and allocate GPU memory.
    """
    det = config.detection
    return YoloDetector(
        model_override or det.active_model,
        confidence=det.confidence,
        iou=det.iou,
        device=device_override or det.device,
        model_dir=det.model_dir,
    )
