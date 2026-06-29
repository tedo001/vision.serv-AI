"""Tests for the laptop-camera test module: NullDetector + diagnostics.

OpenCV is mocked so these run without a real camera or the cv2 package.
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from app.camera import diagnostics
from app.detection.null_detector import NullDetector
from app.detection.runner import DetectionRunner


# --- NullDetector -----------------------------------------------------------
def test_null_detector_detects_nothing() -> None:
    det = NullDetector()
    det.load()
    assert det.name == "passthrough"
    assert det.detect(object()) == []  # type: ignore[arg-type]


def test_runner_with_null_detector_passes_frames_through() -> None:
    """Preview mode: frames flow to display, detections stay empty."""
    class _Src:
        def __init__(self) -> None:
            self.i = 0; self.opened = False; self.released = False
        camera_id = "fake"
        def open(self) -> None: self.opened = True
        def read(self):
            if self.i >= 3:
                return None
            self.i += 1
            f = types.SimpleNamespace(image=np.zeros((4, 4, 3), np.uint8),
                                      camera_id="fake", frame_index=self.i, timestamp=0.0)
            return f
        def release(self) -> None: self.released = True
        @property
        def is_open(self) -> bool: return self.opened and not self.released

    runner = DetectionRunner(_Src(), NullDetector(), annotator=lambda img, d: img)
    runner._run()
    result = runner.latest()
    assert result is not None
    assert result.frame_index == 3
    assert result.detections == []


# --- diagnostics (mocked cv2) -----------------------------------------------
class _FakeCapture:
    def __init__(self, index, *, opens=True, frame=True) -> None:
        self._opens = opens
        self._frame = frame

    def isOpened(self) -> bool:
        return self._opens

    def read(self):
        if self._frame:
            return True, np.zeros((480, 640, 3), dtype=np.uint8)
        return False, None

    def release(self) -> None:
        pass


def _install_fake_cv2(monkeypatch, available_indices: set[int]) -> None:
    fake = types.ModuleType("cv2")

    def VideoCapture(index):  # noqa: N802 - mimic cv2 API
        return _FakeCapture(index, opens=index in available_indices,
                            frame=index in available_indices)

    fake.VideoCapture = VideoCapture
    monkeypatch.setitem(sys.modules, "cv2", fake)


def test_probe_camera_reports_resolution(monkeypatch) -> None:
    _install_fake_cv2(monkeypatch, {0})
    probe = diagnostics.probe_camera(0)
    assert probe.available and probe.width == 640 and probe.height == 480


def test_probe_camera_unavailable(monkeypatch) -> None:
    _install_fake_cv2(monkeypatch, {0})
    probe = diagnostics.probe_camera(3)
    assert not probe.available


def test_list_cameras_returns_only_working(monkeypatch) -> None:
    _install_fake_cv2(monkeypatch, {0, 2})
    found = diagnostics.list_cameras(max_index=3)
    assert [p.index for p in found] == [0, 2]
