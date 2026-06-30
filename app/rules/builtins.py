"""Built-in rules.

Each factory returns a configured rule (a callable). Rules carry a
``rule_name`` attribute used for debounce keys and event attribution. Rules
that depend on specific labels (helmet/fire/…) only fire when a model that
emits those labels is running — they are inert otherwise, by design.
"""

from __future__ import annotations

from app.core.models import BoundingBox, EventSeverity
from app.rules.context import RuleContext, RuleResult

# Common label spellings across datasets.
_NO_HELMET = {"no_helmet", "no-helmet", "nohelmet", "head", "without_helmet"}
_NO_VEST = {"no_vest", "no-vest", "without_vest"}
_FIRE = {"fire", "flame"}
_SMOKE = {"smoke"}
# COCO vehicle/machinery classes — usable for proximity hazards with no training.
_VEHICLES = {"truck", "bus", "car", "motorcycle", "bicycle", "train",
             "forklift", "airplane", "boat"}


def _box_gap(a: BoundingBox, b: BoundingBox) -> float:
    """Shortest pixel distance between two boxes (0 if they overlap/touch)."""
    dx = max(0.0, a.x1 - b.x2, b.x1 - a.x2)
    dy = max(0.0, a.y1 - b.y2, b.y1 - a.y2)
    return (dx * dx + dy * dy) ** 0.5


def _named(fn, name: str):
    fn.rule_name = name  # type: ignore[attr-defined]
    return fn


def no_ppe_rule():
    """Flag PPE violations when a PPE model reports missing helmet/vest."""
    def rule(ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []
        missing_helmet = [d for d in ctx.detections if d.label in _NO_HELMET]
        missing_vest = [d for d in ctx.detections if d.label in _NO_VEST]
        if missing_helmet:
            out.append(RuleResult("ppe_no_helmet", EventSeverity.HIGH,
                                  f"{len(missing_helmet)} worker(s) without a helmet",
                                  tuple(missing_helmet)))
        if missing_vest:
            out.append(RuleResult("ppe_no_vest", EventSeverity.MEDIUM,
                                  f"{len(missing_vest)} worker(s) without a vest",
                                  tuple(missing_vest)))
        return out
    return _named(rule, "no_ppe")


def fire_smoke_rule():
    """Critical/high event when fire or smoke is detected."""
    def rule(ctx: RuleContext) -> list[RuleResult]:
        out: list[RuleResult] = []
        fire = [d for d in ctx.detections if d.label in _FIRE]
        smoke = [d for d in ctx.detections if d.label in _SMOKE]
        if fire:
            out.append(RuleResult("fire", EventSeverity.CRITICAL,
                                  "Fire detected", tuple(fire)))
        if smoke:
            out.append(RuleResult("smoke", EventSeverity.HIGH,
                                  "Smoke detected", tuple(smoke)))
        return out
    return _named(rule, "fire_smoke")


def max_occupancy_rule(threshold: int):
    """Event when the number of people exceeds ``threshold``."""
    def rule(ctx: RuleContext) -> list[RuleResult]:
        n = ctx.count("person")
        if n > threshold:
            return [RuleResult("max_occupancy", EventSeverity.MEDIUM,
                               f"Occupancy {n} exceeds limit of {threshold}")]
        return []
    return _named(rule, "max_occupancy")


def restricted_zone_rule(x1f: float, y1f: float, x2f: float, y2f: float):
    """Event when a person's center enters a zone (fractions of the frame)."""
    def rule(ctx: RuleContext) -> list[RuleResult]:
        zx1, zy1 = x1f * ctx.frame_width, y1f * ctx.frame_height
        zx2, zy2 = x2f * ctx.frame_width, y2f * ctx.frame_height
        hits = []
        for d in ctx.detections:
            if d.label != "person":
                continue
            cx, cy = d.box.center
            if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
                hits.append(d)
        return [
            RuleResult("restricted_zone", EventSeverity.HIGH,
                       "Person in restricted zone", (d,),
                       dedupe_key=str(d.track_id) if d.track_id is not None else "")
            for d in hits
        ]
    return _named(rule, "restricted_zone")


def vehicle_proximity_rule(gap_frac: float = 0.04):
    """Worker dangerously close to a vehicle/machine (struck-by hazard).

    Uses only COCO classes (person + vehicles), so it needs NO custom training.
    ``gap_frac`` is the alert distance as a fraction of the frame width; 0 means
    boxes must overlap.
    """
    def rule(ctx: RuleContext) -> list[RuleResult]:
        threshold = gap_frac * ctx.frame_width
        workers = ctx.by_label("person")
        hazards = [d for d in ctx.detections if d.label in _VEHICLES]
        out: list[RuleResult] = []
        for worker in workers:
            for hazard in hazards:
                gap = _box_gap(worker.box, hazard.box)
                if gap <= threshold:
                    key = f"{worker.track_id}-{hazard.track_id}"
                    out.append(RuleResult(
                        "vehicle_proximity", EventSeverity.HIGH,
                        f"Worker dangerously close to {hazard.label} "
                        f"({gap:.0f}px)", (worker, hazard), dedupe_key=key))
                    break  # one alert per worker per frame
        return out
    return _named(rule, "vehicle_proximity")


def default_rules() -> tuple:
    """A sensible default rule set. Label-driven rules (PPE/fire) stay inert
    until a model emits those labels; proximity/occupancy work on COCO today."""
    return (
        no_ppe_rule(),
        fire_smoke_rule(),
        max_occupancy_rule(25),
        vehicle_proximity_rule(),
    )
