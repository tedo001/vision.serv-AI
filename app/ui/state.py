"""Framework-agnostic presentation state (the UI's read model).

This module deliberately imports **no GUI toolkit**. It defines an observable
``AppState`` that any front-end binds to: the current Tkinter UI today, and a
web or Qt UI tomorrow. The widgets are disposable; this state and the backend
services behind it are not.

Pattern: a minimal observable (a tiny slice of MVVM). Backend engines push
updates into ``AppState`` (e.g. ``state.fps.set(24.0)``); the UI subscribes and
re-renders. The UI never reaches into engines for data, and engines never know
which UI is attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generic, TypeVar

from app.core.models import Alert, Event

T = TypeVar("T")

Unsubscribe = Callable[[], None]


class Observable(Generic[T]):
    """A value that notifies subscribers when it changes."""

    def __init__(self, value: T) -> None:
        self._value = value
        self._subscribers: list[Callable[[T], None]] = []

    @property
    def value(self) -> T:
        return self._value

    def set(self, value: T) -> None:
        # Skip notifying subscribers when the value is unchanged. This avoids
        # redundant UI re-renders from high-frequency producers (e.g. the
        # per-frame stats stream). Equality is best-effort: if a value type
        # can't be compared, fall back to always notifying.
        try:
            if value == self._value:
                self._value = value
                return
        except Exception:  # noqa: BLE001 - uncomparable type: notify anyway
            pass
        self._value = value
        self._notify()

    def update(self, fn: Callable[[T], T]) -> None:
        self.set(fn(self._value))

    def subscribe(
        self, callback: Callable[[T], None], *, immediate: bool = True
    ) -> Unsubscribe:
        """Register ``callback``; returns a function that unsubscribes it.

        When ``immediate`` is true the callback fires once with the current
        value so the UI can render initial state without duplication.
        """
        self._subscribers.append(callback)
        if immediate:
            callback(self._value)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable[[T], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for callback in list(self._subscribers):
            callback(self._value)


class ConnectionStatus(str, Enum):
    """Coarse status used for the top-nav indicators."""

    UNKNOWN = "unknown"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE = "online"


@dataclass(frozen=True, slots=True)
class DetectionStats:
    """Aggregate counters shown in the right panel / dashboard."""

    active_cameras: int = 0
    total_cameras: int = 0
    events_today: int = 0
    active_alerts: int = 0
    detections_per_second: float = 0.0


@dataclass(slots=True)
class AppState:
    """The complete observable state surface the UI binds to.

    Construct one per running application and pass it to the view layer. All
    fields are ``Observable`` so any field can be bound independently.
    """

    product_name: Observable[str] = field(
        default_factory=lambda: Observable("AI Vision Platform")
    )
    active_profile: Observable[str] = field(
        default_factory=lambda: Observable("construction")
    )
    camera_status: Observable[ConnectionStatus] = field(
        default_factory=lambda: Observable(ConnectionStatus.OFFLINE)
    )
    gpu_status: Observable[ConnectionStatus] = field(
        default_factory=lambda: Observable(ConnectionStatus.UNKNOWN)
    )
    gpu_name: Observable[str] = field(default_factory=lambda: Observable("CPU"))
    fps: Observable[float] = field(default_factory=lambda: Observable(0.0))

    # Detection model selection (mirrors config.detection; the engine reads it).
    active_model: Observable[str] = field(
        default_factory=lambda: Observable("yolo26n")
    )
    model_enabled: Observable[bool] = field(default_factory=lambda: Observable(False))
    confidence: Observable[float] = field(default_factory=lambda: Observable(0.45))
    iou: Observable[float] = field(default_factory=lambda: Observable(0.50))

    stats: Observable[DetectionStats] = field(
        default_factory=lambda: Observable(DetectionStats())
    )
    events: Observable[tuple[Event, ...]] = field(
        default_factory=lambda: Observable(())
    )
    alerts: Observable[tuple[Alert, ...]] = field(
        default_factory=lambda: Observable(())
    )
    status_message: Observable[str] = field(
        default_factory=lambda: Observable("Ready")
    )

    @classmethod
    def from_config(
        cls,
        *,
        product_name: str,
        active_profile: str,
        active_model: str = "yolo26n",
        model_enabled: bool = False,
        confidence: float = 0.45,
        iou: float = 0.50,
    ) -> "AppState":
        """Build initial state seeded from the loaded application config."""
        state = cls()
        state.product_name.set(product_name)
        state.active_profile.set(active_profile)
        state.active_model.set(active_model)
        state.model_enabled.set(model_enabled)
        state.confidence.set(confidence)
        state.iou.set(iou)
        return state
