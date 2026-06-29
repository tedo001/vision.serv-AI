"""Tests for the detection runner, device resolution, and capture mapping.

These exercise the orchestration logic with fakes — no OpenCV, torch, or model
weights required — so the vertical slice is verifiable without a GPU or camera.
"""

from __future__ import annotations

import numpy as np

from app.camera.opencv_source import OpenCVCameraSource
from app.core.device import resolve_device
from app.core.models import BoundingBox, CameraSourceType, Detection
from app.detection.runner import DetectionRunner


# --- fakes ------------------------------------------------------------------
class _FakeFrame:
    def __init__(self, idx: int) -> None:
        self.image = np.zeros((8, 8, 3), dtype=np.uint8)
        self.camera_id = "fake"
        self.frame_index = idx
        self.timestamp = float(idx)


class _FakeSource:
    """Yields ``n`` frames then None (end-of-stream), like a finite file."""

    def __init__(self, n: int) -> None:
        self._n = n
        self._i = 0
        self.opened = False
        self.released = False

    @property
    def camera_id(self) -> str:
        return "fake"

    def open(self) -> None:
        self.opened = True

    def read(self):
        if self._i >= self._n:
            return None
        self._i += 1
        return _FakeFrame(self._i)

    def release(self) -> None:
        self.released = True

    @property
    def is_open(self) -> bool:
        return self.opened and not self.released


class _FakeDetector:
    def __init__(self) -> None:
        self.loaded = False

    @property
    def name(self) -> str:
        return "fake"

    def load(self) -> None:
        self.loaded = True

    def detect(self, frame):
        return [Detection("obj", 0.9, BoundingBox(0, 0, 4, 4), "fake")]

    def unload(self) -> None:
        pass


# --- runner -----------------------------------------------------------------
def test_runner_processes_all_frames_then_ends() -> None:
    source = _FakeSource(5)
    detector = _FakeDetector()
    seen = {"count": 0}

    def annotator(image, dets):
        seen["count"] += 1
        return image

    runner = DetectionRunner(source, detector, annotator=annotator)
    runner._run()  # synchronous, deterministic

    assert detector.loaded
    assert source.opened and source.released
    assert seen["count"] == 5
    result = runner.latest()
    assert result is not None and result.frame_index == 5
    assert len(result.detections) == 1


def test_runner_reports_startup_error() -> None:
    class _BadDetector(_FakeDetector):
        def load(self) -> None:
            raise RuntimeError("no weights")

    runner = DetectionRunner(_FakeSource(1), _BadDetector(), annotator=lambda i, d: i)
    runner._run()
    assert runner.error is not None and "no weights" in runner.error
    assert runner.latest() is None


# --- device -----------------------------------------------------------------
def test_resolve_device_explicit_passthrough() -> None:
    assert resolve_device("cpu") == "cpu"
    assert resolve_device("cuda") == "cuda"


def test_resolve_device_auto_is_cpu_without_gpu() -> None:
    # No torch/GPU in the test environment -> auto resolves to cpu.
    assert resolve_device("auto") in {"cpu", "cuda"}


# --- capture target mapping -------------------------------------------------
def test_usb_spec_becomes_int_index() -> None:
    assert OpenCVCameraSource.resolve_target(CameraSourceType.USB, "0") == 0
    assert OpenCVCameraSource.resolve_target(CameraSourceType.USB, 2) == 2


def test_file_and_rtsp_specs_stay_strings() -> None:
    assert OpenCVCameraSource.resolve_target(CameraSourceType.FILE, "a.mp4") == "a.mp4"
    assert OpenCVCameraSource.resolve_target(
        CameraSourceType.RTSP, "rtsp://x") == "rtsp://x"
