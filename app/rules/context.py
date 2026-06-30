"""Inputs and outputs for rule evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.models import Detection, EventSeverity


@dataclass(frozen=True, slots=True)
class RuleContext:
    """Everything a rule needs to decide, for one frame."""

    detections: tuple[Detection, ...]
    frame_width: int
    frame_height: int
    camera_id: str
    profile_id: str
    timestamp: float

    def by_label(self, *labels: str) -> list[Detection]:
        wanted = set(labels)
        return [d for d in self.detections if d.label in wanted]

    def count(self, label: str) -> int:
        return sum(1 for d in self.detections if d.label == label)


@dataclass(frozen=True, slots=True)
class RuleResult:
    """A rule's finding for the frame; the engine turns it into an Event."""

    event_type: str
    severity: EventSeverity
    message: str
    detections: tuple[Detection, ...] = ()
    # Distinguishes simultaneous hits of the same rule (e.g. per track/zone) so
    # they debounce independently.
    dedupe_key: str = ""
