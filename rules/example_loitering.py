"""Example custom rule — drop your own .py files in this folder.

This file shows the contract: expose a ``RULES`` list of callables, each
taking a RuleContext and returning a list of RuleResult. With ByteTrack
enabled (Settings → track), detections carry stable ``track_id`` values, which
lets you reason across frames — here, a naive "too many people lingering".

The platform auto-loads every *.py in this directory at startup.
"""

from __future__ import annotations

from app.core.models import EventSeverity
from app.rules.context import RuleContext, RuleResult


def crowd_forming(ctx: RuleContext) -> list[RuleResult]:
    """Flag when more than 5 people are present at once."""
    people = ctx.by_label("person")
    if len(people) > 5:
        return [RuleResult(
            event_type="crowd_forming",
            severity=EventSeverity.MEDIUM,
            message=f"Crowd forming: {len(people)} people in view",
            detections=tuple(people),
        )]
    return []


crowd_forming.rule_name = "crowd_forming"  # used for event attribution/debounce

RULES = [crowd_forming]
