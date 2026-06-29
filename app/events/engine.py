"""Event engine (Phase 10).

Turns per-frame detections into confirmed, business-meaningful events and
publishes them to registered sinks (database, UI, alerts). To avoid one event
per frame for the same object, emission is debounced per (camera, label):
once an object type fires, it won't fire again for that camera until a cooldown
elapses. This is a pragmatic stand-in for full multi-object tracking (Phase 9);
the interface won't change when real tracking replaces the debounce.
"""

from __future__ import annotations

from app.core.interfaces import EventSink
from app.core.logging_config import get_logger
from app.core.models import Detection, Event, EventSeverity

logger = get_logger(__name__)

# Severity by detected class. Anything unlisted is LOW. Tuned for the COCO
# classes the profiles use today; safety-specific labels (fire/smoke) will map
# to CRITICAL once custom models provide them.
_SEVERITY: dict[str, EventSeverity] = {
    "person": EventSeverity.INFO,
    "truck": EventSeverity.MEDIUM,
    "bus": EventSeverity.MEDIUM,
    "car": EventSeverity.LOW,
    "motorcycle": EventSeverity.MEDIUM,
    "forklift": EventSeverity.HIGH,
    "fire": EventSeverity.CRITICAL,
    "smoke": EventSeverity.HIGH,
    # Action-derived labels (from pose/skeleton analysis).
    "fall": EventSeverity.CRITICAL,
    "fighting": EventSeverity.HIGH,
}


class EventEngine:
    """Generates debounced events from detections and fans them out to sinks."""

    def __init__(
        self,
        *,
        cooldown_seconds: float = 8.0,
        min_confidence: float = 0.0,
        sinks: tuple[EventSink, ...] = (),
    ) -> None:
        self._cooldown = cooldown_seconds
        self._min_confidence = min_confidence
        self._sinks = list(sinks)
        self._last_emit: dict[tuple[str, str], float] = {}

    def add_sink(self, sink: EventSink) -> None:
        self._sinks.append(sink)

    @staticmethod
    def severity_for(label: str) -> EventSeverity:
        return _SEVERITY.get(label, EventSeverity.LOW)

    def evaluate(
        self,
        camera_id: str,
        profile_id: str,
        detections: list[Detection],
        timestamp: float,
    ) -> list[Event]:
        """Return events to emit for this frame and publish them to sinks."""
        # Keep the highest-confidence detection per label this frame.
        best: dict[str, Detection] = {}
        for det in detections:
            if det.confidence < self._min_confidence:
                continue
            current = best.get(det.label)
            if current is None or det.confidence > current.confidence:
                best[det.label] = det

        events: list[Event] = []
        for label, det in best.items():
            key = (camera_id, label)
            # Default to -inf so the first sighting of a label always emits,
            # regardless of the absolute timestamp value.
            if timestamp - self._last_emit.get(key, float("-inf")) < self._cooldown:
                continue
            self._last_emit[key] = timestamp
            event = Event(
                event_type=f"{label}_detected",
                severity=self.severity_for(label),
                camera_id=camera_id,
                profile_id=profile_id,
                source_plugin=det.source_plugin,
                message=f"{label.capitalize()} detected ({det.confidence:.0%})",
                detections=(det,),
                timestamp=timestamp,
            )
            events.append(event)

        for event in events:
            self._publish(event)
        return events

    def reset(self) -> None:
        self._last_emit.clear()

    def _publish(self, event: Event) -> None:
        for sink in self._sinks:
            try:
                sink.handle_event(event)
            except Exception as exc:  # noqa: BLE001 - one bad sink mustn't break others
                logger.error("Event sink %s failed: %s", type(sink).__name__, exc)
