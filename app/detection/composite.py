"""Run several detectors at once and merge their detections.

Lets the user enable multiple models simultaneously — e.g. a fast object model
+ a pose model for falls + a fine-tuned PPE model — without changing the
runner, which still sees a single ``DetectorPlugin``. Each sub-detector tags
its detections with its own ``source_plugin``, so downstream consumers (rules,
events) can tell which model produced what.
"""

from __future__ import annotations

from app.core.interfaces import Frame
from app.core.logging_config import get_logger
from app.core.models import Detection

logger = get_logger(__name__)


class CompositeDetector:
    """A :class:`DetectorPlugin` that fans a frame out to several detectors."""

    def __init__(self, detectors, name: str = "composite") -> None:
        if not detectors:
            raise ValueError("CompositeDetector requires at least one detector")
        self._detectors = list(detectors)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def detectors(self):
        return tuple(self._detectors)

    def load(self) -> None:
        for det in self._detectors:
            det.load()

    def detect(self, frame: Frame) -> list[Detection]:
        merged: list[Detection] = []
        for det in self._detectors:
            merged.extend(det.detect(frame))
        return merged

    def unload(self) -> None:
        for det in self._detectors:
            det.unload()
