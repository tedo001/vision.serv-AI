"""Domain models.

Immutable-by-default dataclasses describing the core vocabulary of the
platform: detections, tracked objects, events, and alerts. These types form
the contract between the detection engine, tracking engine, event engine,
alert system, and persistence layer.

Design notes:
- Frame pixel data (numpy arrays) is intentionally NOT stored on these
  models. Models carry lightweight metadata; raw frames are passed
  separately to avoid copying megabytes of image data through the event bus
  and into the database.
- ``frozen=True`` where the value is a snapshot of a moment in time. Mutable
  state (e.g. a track that accumulates positions) is explicitly not frozen.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================================
# Enumerations
# ============================================================================
class EventSeverity(str, Enum):
    """Operational severity of a generated event.

    Inherits from ``str`` so values serialize cleanly to YAML/JSON/SQLite
    without custom encoders.
    """

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CameraSourceType(str, Enum):
    """Supported camera/source backends."""

    USB = "usb"
    RTSP = "rtsp"
    IP = "ip"
    FILE = "file"


# ============================================================================
# Geometry
# ============================================================================
@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned bounding box in absolute pixel coordinates.

    Stored as top-left (x1, y1) and bottom-right (x2, y2) corners, the
    convention used by most detection backbones (incl. YOLO xyxy output).
    """

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0

    def iou(self, other: "BoundingBox") -> float:
        """Intersection-over-Union with another box (0.0 - 1.0)."""
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0


# ============================================================================
# Detection
# ============================================================================
@dataclass(frozen=True, slots=True)
class Detection:
    """A single object detected in one frame by one detector/plugin."""

    label: str
    confidence: float
    box: BoundingBox
    source_plugin: str
    class_id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class TrackedObject:
    """An object followed across frames by the tracking engine.

    Mutable: its position history and last-seen timestamp evolve over time.
    """

    track_id: int
    label: str
    box: BoundingBox
    confidence: float
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    hit_count: int = 1

    @property
    def age_seconds(self) -> float:
        return self.last_seen - self.first_seen


# ============================================================================
# Events & Alerts
# ============================================================================
@dataclass(frozen=True, slots=True)
class Event:
    """A confirmed, business-meaningful occurrence.

    Detections are raw signal; an Event is what survives the event engine's
    confirmation logic (e.g. "no helmet for 3 continuous seconds"). Events
    are persisted and may escalate into Alerts.
    """

    event_type: str
    severity: EventSeverity
    camera_id: str
    profile_id: str
    source_plugin: str
    message: str
    detections: tuple[Detection, ...] = ()
    screenshot_path: Optional[str] = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class Alert:
    """A user-facing notification derived from an Event by alert policy.

    Separating Alert from Event keeps detection semantics (what happened)
    independent from notification policy (who is told, how loudly).
    """

    event: Event
    requires_acknowledgement: bool = False
    play_sound: bool = False
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
