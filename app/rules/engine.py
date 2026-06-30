"""The rule engine: evaluate rules, debounce, and emit events to sinks."""

from __future__ import annotations

from typing import Callable

from app.core.interfaces import EventSink
from app.core.logging_config import get_logger
from app.core.models import Event
from app.rules.context import RuleContext, RuleResult

logger = get_logger(__name__)

# A rule is any callable taking a context and returning findings.
Rule = Callable[[RuleContext], list[RuleResult]]


class RuleEngine:
    """Runs a set of rules per frame, debounces, and publishes events."""

    def __init__(
        self,
        rules: tuple[Rule, ...] = (),
        *,
        cooldown_seconds: float = 8.0,
        sinks: tuple[EventSink, ...] = (),
    ) -> None:
        self._rules = list(rules)
        self._cooldown = cooldown_seconds
        self._sinks = list(sinks)
        self._last_emit: dict[tuple[str, str, str], float] = {}

    def add_rule(self, rule: Rule) -> None:
        self._rules.append(rule)

    def add_sink(self, sink: EventSink) -> None:
        self._sinks.append(sink)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def evaluate(self, ctx: RuleContext) -> list[Event]:
        """Run every rule, debounce results, publish + return new events."""
        events: list[Event] = []
        for rule in self._rules:
            try:
                results = rule(ctx) or []
            except Exception as exc:  # noqa: BLE001 - a bad rule mustn't crash the loop
                logger.error("Rule %s raised: %s", getattr(rule, "__name__", rule), exc)
                continue
            for result in results:
                event = self._maybe_emit(rule, result, ctx)
                if event is not None:
                    events.append(event)

        for event in events:
            self._publish(event)
        return events

    def reset(self) -> None:
        self._last_emit.clear()

    # -- internal ------------------------------------------------------------
    def _maybe_emit(self, rule: Rule, result: RuleResult, ctx: RuleContext) -> Event | None:
        rule_name = getattr(rule, "rule_name", getattr(rule, "__name__", "rule"))
        key = (rule_name, result.event_type, f"{ctx.camera_id}:{result.dedupe_key}")
        if ctx.timestamp - self._last_emit.get(key, float("-inf")) < self._cooldown:
            return None
        self._last_emit[key] = ctx.timestamp
        return Event(
            event_type=result.event_type,
            severity=result.severity,
            camera_id=ctx.camera_id,
            profile_id=ctx.profile_id,
            source_plugin=f"rule:{rule_name}",
            message=result.message,
            detections=result.detections,
            timestamp=ctx.timestamp,
        )

    def _publish(self, event: Event) -> None:
        for sink in self._sinks:
            try:
                sink.handle_event(event)
            except Exception as exc:  # noqa: BLE001
                logger.error("Event sink %s failed: %s", type(sink).__name__, exc)
