"""Bridges configuration to a ready-to-use detector.

A thin factory the application (and, in Phase 8, the detection engine) uses to
turn the user's selected model + thresholds into a ``YoloDetector``. Keeping
this in one place means the "which model, what thresholds" decision is made
from config/state and nowhere else.
"""

from __future__ import annotations

from pathlib import Path

from app.config.settings import AppConfig
from app.core.logging_config import get_logger
from app.detection.composite import CompositeDetector
from app.detection.model_catalog import MODELS, ModelInfo, register_model
from app.detection.yolo_detector import YoloDetector

logger = get_logger(__name__)


def available_models() -> tuple[ModelInfo, ...]:
    """All selectable models, in catalog order."""
    return tuple(MODELS.values())


def discover_custom_models(model_dir: str | Path) -> list[ModelInfo]:
    """Register any custom .pt weights found in ``model_dir`` as selectable models.

    Lets trained weights (e.g. produced by tools/train.py) appear in the model
    picker without code changes. A filename containing "pose" is treated as a
    pose model; everything else as object detection.
    """
    directory = Path(model_dir)
    if not directory.is_dir():
        return []
    known_weights = {m.weights for m in MODELS.values()}
    discovered: list[ModelInfo] = []
    for path in sorted(directory.glob("*.pt")):
        if path.name in known_weights:
            continue  # a built-in model's weights, not a custom one
        info = ModelInfo(
            key=f"custom:{path.stem}",
            display_name=f"Custom — {path.stem}",
            weights=path.name,
            family="Custom",
            size_label="—",
            profile="custom",
            approx_size_mb=max(1, path.stat().st_size // (1024 * 1024)),
            description=f"Custom-trained weights ({path.name}).",
            task="pose" if "pose" in path.stem.lower() else "detect",
        )
        register_model(info)
        discovered.append(info)
        logger.info("Registered custom model %s", info.key)
    return discovered


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
        track=det.track,
    )


def build_composite(
    config: AppConfig,
    *,
    device_override: str | None = None,
):
    """Build a detector for ALL enabled models.

    Returns a single ``YoloDetector`` when one model is enabled, or a
    ``CompositeDetector`` running them together. Unknown keys are skipped with
    a warning so one bad entry doesn't break detection.
    """
    det = config.detection
    detectors = []
    for key in det.effective_models:
        if key not in MODELS:
            logger.warning("Skipping unknown enabled model: %s", key)
            continue
        detectors.append(YoloDetector(
            key, confidence=det.confidence, iou=det.iou,
            device=device_override or det.device, model_dir=det.model_dir,
            track=det.track,
        ))
    if not detectors:
        raise ValueError("No valid models enabled for detection.")
    if len(detectors) == 1:
        return detectors[0]
    return CompositeDetector(detectors, name="+".join(det.effective_models))
