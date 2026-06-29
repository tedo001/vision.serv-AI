"""A no-op detector that returns no detections.

Used to exercise the capture → display pipeline without loading a model — for
example the Video Detection tab's "Preview only" mode, which lets a user
verify their laptop camera works before downloading any model weights.

Implements the core ``DetectorPlugin`` port, so it drops into ``DetectionRunner``
exactly like a real detector.
"""

from __future__ import annotations

from app.core.interfaces import Frame
from app.core.models import Detection


class NullDetector:
    """Passthrough detector: loads instantly, detects nothing."""

    @property
    def name(self) -> str:
        return "passthrough"

    def load(self) -> None:  # nothing to load
        return None

    def detect(self, frame: Frame) -> list[Detection]:
        return []

    def unload(self) -> None:
        return None
