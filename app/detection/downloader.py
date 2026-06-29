"""Pre-download model weights into the configured model directory.

By default Ultralytics fetches weights on first inference, which stalls the
very first detection run. This module lets the user download a model ahead of
time from Settings and reports whether a model is already present.

Weights are stored in ``detection.model_dir`` so the local copy is explicit
and ``YoloDetector`` loads it directly. ``ultralytics`` is imported lazily.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.exceptions import DetectionError
from app.core.logging_config import get_logger
from app.detection.model_catalog import ModelInfo

logger = get_logger(__name__)


def weights_path(info: ModelInfo, model_dir: str | Path) -> Path:
    """The canonical local path for a model's weights."""
    return Path(model_dir) / info.weights


def is_downloaded(info: ModelInfo, model_dir: str | Path) -> bool:
    """True if the weights already exist locally."""
    return weights_path(info, model_dir).is_file()


def download_model(info: ModelInfo, model_dir: str | Path) -> Path:
    """Download ``info`` weights into ``model_dir``; return the local path.

    Idempotent: a no-op if the file already exists. Raises ``DetectionError``
    with a clear message on any failure (no network, ultralytics missing, etc).
    """
    target = weights_path(info, model_dir)
    if target.is_file():
        return target

    try:
        from ultralytics import YOLO  # deferred heavy import
    except ImportError as exc:
        raise DetectionError(
            "ultralytics is not installed. Run 'pip install ultralytics' to "
            "download model weights."
        ) from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Instantiating by bare name triggers Ultralytics' download.
        model = YOLO(info.weights)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise DetectionError(
            f"Failed to download {info.display_name} ({info.weights}): {exc}"
        ) from exc

    # Locate the file Ultralytics produced and move it under model_dir.
    candidates = [getattr(model, "ckpt_path", None), info.weights]
    source = next((Path(c) for c in candidates if c and Path(c).is_file()), None)
    if source is None:
        raise DetectionError(
            f"Download reported success but {info.weights} was not found on disk."
        )
    if source.resolve() != target.resolve():
        shutil.move(str(source), str(target))
    logger.info("Downloaded %s to %s", info.display_name, target)
    return target
