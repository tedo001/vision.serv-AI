"""Tests for the model catalog, detector mapping, and config persistence."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from app.config.manager import ConfigManager
from app.core.exceptions import DetectionError
from app.detection.downloader import download_model, is_downloaded, weights_path
from app.detection.model_catalog import MODELS, get_model, is_known_model
from app.detection.model_manager import (
    available_models,
    build_detector,
    discover_custom_models,
)
from app.detection.yolo_detector import YoloDetector


# --- catalog ----------------------------------------------------------------
def test_catalog_contains_requested_models() -> None:
    for key in ("yolo11n", "yolo26n", "yolo26x"):
        assert is_known_model(key)
        assert get_model(key).weights.endswith(".pt")


def test_get_model_is_case_insensitive_and_safe() -> None:
    assert get_model("YOLO26X") is MODELS["yolo26x"]
    assert get_model("nope") is None


def test_available_models_matches_catalog() -> None:
    assert len(available_models()) == len(MODELS)


# --- config persistence -----------------------------------------------------
def test_update_detection_persists_and_validates(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    manager = ConfigManager(cfg_file)
    manager.load()

    updated = manager.update_detection(
        active_model="yolo26x", enabled=True, confidence=0.6, iou=0.4
    )
    assert updated.detection.active_model == "yolo26x"
    assert updated.detection.enabled is True
    assert updated.detection.confidence == 0.6

    # Round-trips through disk.
    reloaded = ConfigManager(cfg_file).load()
    assert reloaded.detection.active_model == "yolo26x"
    assert reloaded.detection.enabled is True
    assert reloaded.detection.iou == 0.4


def test_update_detection_rejects_bad_threshold(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "c.yaml")
    manager.load()
    with pytest.raises(Exception):
        manager.update_detection(confidence=2.0)


# --- downloader -------------------------------------------------------------
def test_weights_path_and_is_downloaded(tmp_path: Path) -> None:
    info = MODELS["yolo26n"]
    assert not is_downloaded(info, tmp_path)
    # Simulate a present weights file.
    (tmp_path / info.weights).write_bytes(b"fake-weights")
    assert is_downloaded(info, tmp_path)
    assert weights_path(info, tmp_path).name == info.weights


def test_download_is_noop_when_already_present(tmp_path: Path) -> None:
    info = MODELS["yolo11n"]
    target = tmp_path / info.weights
    target.write_bytes(b"x")
    # Must not import/download anything when the file already exists.
    assert download_model(info, tmp_path) == target


# --- custom model discovery -------------------------------------------------
def test_discover_custom_models_registers_and_is_selectable(tmp_path: Path) -> None:
    (tmp_path / "safety_v1.pt").write_bytes(b"x")
    (tmp_path / "guard-pose.pt").write_bytes(b"x")
    (tmp_path / "yolo26n.pt").write_bytes(b"x")  # built-in weights -> ignored
    (tmp_path / "notes.txt").write_text("ignore me")

    try:
        found = discover_custom_models(tmp_path)
        keys = {m.key for m in found}
        assert keys == {"custom:safety_v1", "custom:guard-pose"}
        # Task inferred from filename.
        tasks = {m.key: m.task for m in found}
        assert tasks["custom:guard-pose"] == "pose"
        assert tasks["custom:safety_v1"] == "detect"
        # Selectable like any model, and usable by build_detector.
        assert is_known_model("custom:safety_v1")
        from app.config.manager import ConfigManager
        cfg = ConfigManager(tmp_path / "c.yaml")
        cfg.load()
        cfg.update_detection(active_model="custom:safety_v1")
        det = build_detector(cfg.config)
        assert det.name == "custom:safety_v1"
    finally:
        for key in ("custom:safety_v1", "custom:guard-pose"):
            MODELS.pop(key, None)


def test_discover_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert discover_custom_models(tmp_path / "nope") == []


# --- detector ---------------------------------------------------------------
def test_unknown_model_raises() -> None:
    with pytest.raises(DetectionError):
        YoloDetector("does-not-exist")


def test_detect_before_load_raises() -> None:
    det = YoloDetector("yolo26n")
    frame = _FakeFrame()
    with pytest.raises(DetectionError):
        det.detect(frame)


def test_build_detector_from_config_uses_active_model(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "c.yaml")
    manager.load()
    manager.update_detection(active_model="yolo11n", confidence=0.7, iou=0.3)
    det = build_detector(manager.config)
    assert det.name == "yolo11n"
    assert det._confidence == 0.7  # type: ignore[attr-defined]


def test_result_mapping_to_detections() -> None:
    """Map a fake ultralytics result without loading real weights."""
    det = YoloDetector("yolo26n")
    det._model = object()  # type: ignore[attr-defined]  # bypass load()
    results = [_FakeResult(
        names={0: "person", 7: "truck"},
        boxes=[_FakeBox([10, 20, 110, 220], 0.91, 0),
               _FakeBox([0, 0, 50, 50], 0.77, 7)],
    )]
    detections = det._map_results(results)  # type: ignore[attr-defined]
    assert [d.label for d in detections] == ["person", "truck"]
    assert detections[0].confidence == pytest.approx(0.91)
    assert detections[0].box.width == 100
    assert detections[0].source_plugin == "yolo26n"


# --- test doubles -----------------------------------------------------------
@dataclass
class _FakeFrame:
    image: np.ndarray = None  # type: ignore[assignment]
    camera_id: str = "cam0"
    frame_index: int = 0
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.image is None:
            self.image = np.zeros((4, 4, 3), dtype=np.uint8)


class _FakeBox:
    def __init__(self, xyxy, conf, cls) -> None:
        self.xyxy = [np.array(xyxy, dtype=float)]
        self.conf = [conf]
        self.cls = [cls]


class _FakeResult:
    def __init__(self, names, boxes) -> None:
        self.names = names
        self.boxes = boxes
