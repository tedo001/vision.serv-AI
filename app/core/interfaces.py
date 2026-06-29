"""Core abstractions (ports).

These ``Protocol`` definitions are the seams of the system. The core depends
only on these interfaces; concrete implementations (OpenCV cameras, YOLO
detectors, SQLite sinks, Tkinter views) live in outer layers and are wired in
at runtime via the DI container.

Using ``typing.Protocol`` (structural typing) over abstract base classes is a
deliberate choice: plugins and adapters satisfy these contracts simply by
shape, so third-party plugins need not import or subclass our base classes to
be compatible. This keeps the plugin ecosystem loosely coupled.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

import numpy as np

from app.core.models import Detection, Event, TrackedObject


@runtime_checkable
class Frame(Protocol):
    """A captured frame plus the metadata needed to attribute it."""

    image: np.ndarray
    camera_id: str
    frame_index: int
    timestamp: float


@runtime_checkable
class CameraSource(Protocol):
    """A source of frames: USB, RTSP, IP, or local file."""

    @property
    def camera_id(self) -> str: ...

    def open(self) -> None: ...

    def read(self) -> Optional[Frame]:
        """Return the next frame, or None if the stream has ended."""
        ...

    def release(self) -> None: ...

    @property
    def is_open(self) -> bool: ...


@runtime_checkable
class DetectorPlugin(Protocol):
    """An AI module that finds objects/conditions in a frame.

    This is the contract every plugin in :mod:`app.plugins` satisfies
    (helmet, vest, fire, fall, etc.). Profiles enable a subset of plugins.
    """

    @property
    def name(self) -> str:
        """Unique, stable plugin identifier (e.g. ``"helmet"``)."""
        ...

    def load(self) -> None:
        """Load model weights / allocate resources. Called once at startup."""
        ...

    def detect(self, frame: Frame) -> list[Detection]:
        """Run inference on a single frame."""
        ...

    def unload(self) -> None:
        """Release resources. Called on shutdown or profile switch."""
        ...


@runtime_checkable
class Tracker(Protocol):
    """Associates detections across frames into stable tracks."""

    def update(self, detections: list[Detection]) -> list[TrackedObject]: ...

    def reset(self) -> None: ...


@runtime_checkable
class EventSink(Protocol):
    """A consumer of confirmed events (database, alert system, UI, reports).

    The event engine publishes to all registered sinks. Sinks must be
    non-blocking or fast; slow work belongs on a background queue.
    """

    def handle_event(self, event: Event) -> None: ...
