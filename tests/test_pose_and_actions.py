"""Tests for pose/skeleton support and action (fall) detection."""

from __future__ import annotations

import types

import numpy as np

from app.core.models import BoundingBox, Detection, EventSeverity
from app.detection.actions import FallActionDetector, detect_actions, is_fallen
from app.detection.model_catalog import MODELS, get_model
from app.detection.runner import DetectionRunner
from app.detection.yolo_detector import YoloDetector
from app.events.engine import EventEngine


class _FakeBox:
    def __init__(self, xyxy, conf, cls) -> None:
        self.xyxy = [np.array(xyxy, dtype=float)]
        self.conf = [conf]
        self.cls = [cls]


# --- catalog ----------------------------------------------------------------
def test_pose_models_present_and_tagged() -> None:
    pose = get_model("yolo11n-pose")
    assert pose is not None and pose.task == "pose"
    assert pose.weights == "yolo11n-pose.pt"
    # Detection models keep the default task.
    assert MODELS["yolo26n"].task == "detect"


# --- keypoint extraction ----------------------------------------------------
def test_detector_maps_pose_keypoints() -> None:
    det = YoloDetector("yolo11n-pose")
    det._model = object()  # bypass load
    # Build a fake pose result: one person box + 17 keypoints.
    kpts = np.zeros((1, 17, 3), dtype=float)
    kpts[0, 5] = (10, 20, 0.9)   # left shoulder
    result = types.SimpleNamespace(
        names={0: "person"},
        boxes=[_FakeBox([0, 0, 50, 100], 0.9, 0)],
        keypoints=types.SimpleNamespace(data=kpts),
    )
    out = det._map_results([result])
    assert len(out) == 1
    assert len(out[0].keypoints) == 17
    assert out[0].keypoints[5] == (10.0, 20.0, 0.9)


# --- fall heuristics --------------------------------------------------------
def _person_with_torso(dx: float, dy: float) -> Detection:
    """A person whose shoulders→hips axis has the given horizontal/vertical span."""
    kpts = [(0.0, 0.0, 0.0)] * 17
    kpts[5] = (100.0, 100.0, 0.9)            # L shoulder
    kpts[6] = (100.0, 100.0, 0.9)            # R shoulder
    kpts[11] = (100.0 + dx, 100.0 + dy, 0.9)  # L hip
    kpts[12] = (100.0 + dx, 100.0 + dy, 0.9)  # R hip
    return Detection("person", 0.9, BoundingBox(0, 0, 50, 100), "pose",
                     keypoints=tuple(kpts))


def test_standing_person_not_fallen() -> None:
    assert is_fallen(_person_with_torso(dx=5, dy=80)) is False   # vertical torso


def test_horizontal_torso_is_fall() -> None:
    assert is_fallen(_person_with_torso(dx=80, dy=5)) is True     # horizontal torso


def test_box_aspect_fallback_detects_lying_person() -> None:
    # No keypoints: wide-and-short box => lying down.
    lying = Detection("person", 0.8, BoundingBox(0, 0, 200, 80), "yolo26n")
    standing = Detection("person", 0.8, BoundingBox(0, 0, 60, 180), "yolo26n")
    assert is_fallen(lying) is True
    assert is_fallen(standing) is False


def test_detect_actions_emits_fall_for_people_only() -> None:
    dets = [
        _person_with_torso(dx=80, dy=5),                       # fallen person
        Detection("truck", 0.9, BoundingBox(0, 0, 50, 50), "x"),  # ignored
    ]
    actions = detect_actions(dets)
    assert [a.label for a in actions] == ["fall"]
    assert actions[0].source_plugin.endswith(":action")


# --- fall confirmation window (false-positive fix) --------------------------
class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_fall_requires_sustained_window() -> None:
    """A momentary horizontal pose must NOT alert; a sustained one must."""
    clock = _Clock()
    det = FallActionDetector(confirm_seconds=1.0, clock=clock)
    fallen = _person_with_torso(dx=80, dy=5)
    fallen = Detection("person", 0.9, fallen.box, "pose",
                       keypoints=fallen.keypoints, track_id=1)

    clock.t = 0.0
    assert det([fallen]) == []          # first frame: not confirmed yet
    clock.t = 0.5
    assert det([fallen]) == []          # 0.5s: still within window
    clock.t = 1.1
    out = det([fallen])                 # >1s sustained: fires
    assert [d.label for d in out] == ["fall"]


def test_brief_pose_then_recovery_does_not_alert() -> None:
    clock = _Clock()
    det = FallActionDetector(confirm_seconds=1.0, clock=clock)
    person = _person_with_torso(dx=80, dy=5)
    fallen = Detection("person", 0.9, person.box, "pose",
                       keypoints=person.keypoints, track_id=1)
    standing = Detection("person", 0.9, BoundingBox(0, 0, 50, 180), "pose", track_id=1)

    clock.t = 0.0
    det([fallen])
    clock.t = 0.4
    det([fallen])
    clock.t = 0.6
    assert det([standing]) == []        # recovered before 1s -> timer resets
    clock.t = 1.2
    assert det([standing]) == []        # still standing -> no alert


# --- fall -> event severity -------------------------------------------------
def test_fall_maps_to_critical_event() -> None:
    assert EventEngine.severity_for("fall") == EventSeverity.CRITICAL
    engine = EventEngine(cooldown_seconds=0.0)
    fall = Detection("fall", 0.9, BoundingBox(0, 0, 50, 50), "pose:action")
    events = engine.evaluate("cam0", "construction", [fall], 1.0)
    assert events and events[0].severity == EventSeverity.CRITICAL


# --- runner runs action analysis after filtering ----------------------------
class _Src:
    camera_id = "cam0"

    def __init__(self) -> None:
        self.i = 0

    def open(self) -> None: ...
    def release(self) -> None: ...

    @property
    def is_open(self) -> bool:
        return True

    def read(self):
        if self.i >= 1:
            return None
        self.i += 1
        return types.SimpleNamespace(image=np.zeros((4, 4, 3), np.uint8),
                                     camera_id="cam0", frame_index=1, timestamp=1.0)


class _FallDetector:
    name = "pose"

    def load(self) -> None: ...
    def unload(self) -> None: ...

    def detect(self, frame):
        return [_person_with_torso(dx=80, dy=5)]  # a fallen person


def test_runner_generates_fall_events() -> None:
    engine = EventEngine(cooldown_seconds=0.0)
    runner = DetectionRunner(
        _Src(), _FallDetector(), annotator=lambda img, d: img,
        class_filter=frozenset({"person"}),   # fall is appended AFTER filtering
        event_engine=engine, profile_id="construction", action_fn=detect_actions)
    runner._run()
    labels = {e.event_type for e in runner.drain_events()}
    assert "fall_detected" in labels
    assert "person_detected" in labels
