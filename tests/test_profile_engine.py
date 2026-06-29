"""Tests for the profile engine and profile-driven detection filtering."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.config.manager import ConfigManager
from app.core.exceptions import ProfileError
from app.core.models import BoundingBox, Detection
from app.detection.runner import DetectionRunner
from app.profiles.catalog import PROFILES
from app.profiles.engine import ProfileEngine, relevant_classes
from app.ui.state import AppState


def test_every_profile_defines_detectable_classes() -> None:
    for profile in PROFILES.values():
        assert profile.coco_classes, f"{profile.key} has no coco_classes"
        assert "person" in profile.coco_classes  # people matter everywhere


def test_relevant_classes_known_and_unknown() -> None:
    assert "truck" in relevant_classes("construction")
    assert relevant_classes("does-not-exist") == frozenset()


def test_apply_profile_updates_state_and_persists(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "c.yaml")
    manager.load()
    state = AppState()
    engine = ProfileEngine(manager, state)

    engine.apply_profile("warehouse")
    assert state.active_profile.value == "warehouse"
    # Persisted to disk.
    assert ConfigManager(tmp_path / "c.yaml").load().active_profile == "warehouse"


def test_apply_unknown_profile_raises(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "c.yaml")
    manager.load()
    engine = ProfileEngine(manager, AppState())
    with pytest.raises(ProfileError):
        engine.apply_profile("spaceship")


# --- runner class filtering -------------------------------------------------
class _Src:
    camera_id = "fake"

    def __init__(self) -> None:
        self.i = 0
        self.opened = self.released = False

    def open(self) -> None:
        self.opened = True

    def read(self):
        if self.i >= 1:
            return None
        self.i += 1
        import types
        return types.SimpleNamespace(image=np.zeros((4, 4, 3), np.uint8),
                                     camera_id="fake", frame_index=1, timestamp=0.0)

    def release(self) -> None:
        self.released = True

    @property
    def is_open(self) -> bool:
        return self.opened and not self.released


class _MixedDetector:
    name = "fake"

    def load(self) -> None: ...
    def unload(self) -> None: ...

    def detect(self, frame):
        box = BoundingBox(0, 0, 4, 4)
        return [
            Detection("person", 0.9, box, "fake"),
            Detection("truck", 0.8, box, "fake"),
            Detection("zebra", 0.7, box, "fake"),
        ]


def test_class_filter_keeps_only_relevant_detections() -> None:
    runner = DetectionRunner(
        _Src(), _MixedDetector(), annotator=lambda img, d: img,
        class_filter=frozenset({"person", "truck"}))
    runner._run()
    result = runner.latest()
    assert {d.label for d in result.detections} == {"person", "truck"}


def test_no_filter_keeps_all_detections() -> None:
    runner = DetectionRunner(_Src(), _MixedDetector(), annotator=lambda img, d: img)
    runner._run()
    result = runner.latest()
    assert len(result.detections) == 3
