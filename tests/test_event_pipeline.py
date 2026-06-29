"""End-to-end tests for the event pipeline and per-profile detection.

Covers: event engine debounce/severity, SQLite persistence, runner→event
integration, and that detection is correctly configured for all 7 industry
profiles. No GUI, OpenCV, torch, or model weights required.
"""

from __future__ import annotations

import types
from pathlib import Path

import numpy as np

from app.core.models import BoundingBox, Detection, EventSeverity
from app.database.sqlite_sink import SqliteEventSink
from app.detection.runner import DetectionRunner
from app.events.engine import EventEngine
from app.profiles.catalog import PROFILES
from app.profiles.engine import relevant_classes


# --- event engine -----------------------------------------------------------
def _dets(*labels: str) -> list[Detection]:
    box = BoundingBox(0, 0, 4, 4)
    return [Detection(l, 0.9, box, "yolo26n") for l in labels]


def test_engine_emits_one_event_per_label_then_debounces() -> None:
    engine = EventEngine(cooldown_seconds=10.0)
    first = engine.evaluate("cam0", "construction", _dets("person", "truck"), 100.0)
    assert {e.event_type for e in first} == {"person_detected", "truck_detected"}
    # Same labels within cooldown -> no new events.
    again = engine.evaluate("cam0", "construction", _dets("person"), 105.0)
    assert again == []
    # After cooldown -> emits again.
    later = engine.evaluate("cam0", "construction", _dets("person"), 111.0)
    assert len(later) == 1


def test_engine_severity_mapping() -> None:
    assert EventEngine.severity_for("truck") == EventSeverity.MEDIUM
    assert EventEngine.severity_for("person") == EventSeverity.INFO
    assert EventEngine.severity_for("unknown") == EventSeverity.LOW


def test_engine_publishes_to_sinks() -> None:
    received = []
    engine = EventEngine(sinks=(types.SimpleNamespace(handle_event=received.append),))
    engine.evaluate("cam0", "office", _dets("laptop"), 1.0)
    assert len(received) == 1 and received[0].event_type == "laptop_detected"


# --- sqlite sink ------------------------------------------------------------
def test_sqlite_sink_persists_and_counts(tmp_path: Path) -> None:
    sink = SqliteEventSink(tmp_path / "events.db")
    engine = EventEngine(sinks=(sink,))
    engine.evaluate("cam0", "construction", _dets("person", "truck"), 1.0)
    assert sink.count_events() == 2
    rows = sink.recent()
    assert {r["event_type"] for r in rows} == {"person_detected", "truck_detected"}
    sink.close()

    # Survives reopen (real persistence).
    reopened = SqliteEventSink(tmp_path / "events.db")
    assert reopened.count_events() == 2
    reopened.close()


# --- runner integration -----------------------------------------------------
class _Src:
    camera_id = "cam0"

    def __init__(self, n: int) -> None:
        self.i = 0
        self._n = n

    def open(self) -> None: ...
    def release(self) -> None: ...

    @property
    def is_open(self) -> bool:
        return True

    def read(self):
        if self.i >= self._n:
            return None
        self.i += 1
        return types.SimpleNamespace(image=np.zeros((4, 4, 3), np.uint8),
                                     camera_id="cam0", frame_index=self.i,
                                     timestamp=float(self.i))


class _Detector:
    name = "yolo26n"

    def load(self) -> None: ...
    def unload(self) -> None: ...

    def detect(self, frame):
        return _dets("person", "truck", "zebra")


def test_runner_generates_and_buffers_events(tmp_path: Path) -> None:
    sink = SqliteEventSink(tmp_path / "e.db")
    engine = EventEngine(cooldown_seconds=0.0, sinks=(sink,))
    runner = DetectionRunner(
        _Src(2), _Detector(), annotator=lambda img, d: img,
        class_filter=relevant_classes("construction"),  # excludes "zebra"
        event_engine=engine, profile_id="construction")
    runner._run()

    drained = runner.drain_events()
    labels = {e.event_type for e in drained}
    assert "zebra_detected" not in labels        # filtered out by profile
    assert "person_detected" in labels and "truck_detected" in labels
    assert sink.count_events() >= 2
    sink.close()


# --- detection configured for every profile ---------------------------------
def test_detection_configured_for_all_profiles() -> None:
    """Each profile filters a mixed detection set to only its own classes."""
    mixed = ["person", "truck", "car", "laptop", "cell phone", "bed",
             "handbag", "zebra", "elephant"]
    for key, profile in PROFILES.items():
        allowed = relevant_classes(key)
        assert allowed, f"{key} has no detection classes"
        kept = [l for l in mixed if l in allowed]
        # Every kept label is one the profile declared; nothing leaks through.
        assert set(kept) <= set(profile.coco_classes)
        # "zebra"/"elephant" are never relevant to a workplace profile.
        assert "zebra" not in kept and "elephant" not in kept
