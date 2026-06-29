"""Tests for core domain models and geometry."""

from __future__ import annotations

from app.core.models import BoundingBox, Detection, Event, EventSeverity


def test_bounding_box_geometry() -> None:
    box = BoundingBox(10, 20, 110, 70)
    assert box.width == 100
    assert box.height == 50
    assert box.area == 5000
    assert box.center == (60.0, 45.0)


def test_iou_identical_boxes_is_one() -> None:
    box = BoundingBox(0, 0, 10, 10)
    assert box.iou(box) == 1.0


def test_iou_disjoint_boxes_is_zero() -> None:
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(20, 20, 30, 30)
    assert a.iou(b) == 0.0


def test_iou_half_overlap() -> None:
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(5, 0, 15, 10)
    # intersection 50, union 150 -> 1/3
    assert abs(a.iou(b) - (1 / 3)) < 1e-9


def test_event_severity_serializes_as_string() -> None:
    assert EventSeverity.CRITICAL == "critical"
    assert EventSeverity.CRITICAL.value == "critical"


def test_event_gets_unique_ids() -> None:
    box = BoundingBox(0, 0, 1, 1)
    det = Detection(label="person", confidence=0.9, box=box, source_plugin="person")
    e1 = Event(
        event_type="no_helmet",
        severity=EventSeverity.HIGH,
        camera_id="cam1",
        profile_id="construction",
        source_plugin="helmet",
        message="No helmet",
        detections=(det,),
    )
    e2 = Event(
        event_type="no_helmet",
        severity=EventSeverity.HIGH,
        camera_id="cam1",
        profile_id="construction",
        source_plugin="helmet",
        message="No helmet",
    )
    assert e1.event_id != e2.event_id
