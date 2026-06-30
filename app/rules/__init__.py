"""Rule engine (custom Python rules).

Detection answers "what objects are present"; **rules** encode the business
logic of "what is a violation / incident worth an event". A rule is just a
Python callable that inspects a :class:`RuleContext` (the frame's detections,
tracks, size, camera, profile) and returns zero or more :class:`RuleResult`.

Built-in rules live in :mod:`app.rules.builtins`; users can add their own by
dropping a ``.py`` file in the ``rules/`` directory (see
:func:`app.rules.loader.load_rules_from_dir`). This keeps incident logic in
plain, version-controllable Python — no DSL to learn — and fully decoupled
from the detection models.
"""

from __future__ import annotations

from app.rules.context import RuleContext, RuleResult
from app.rules.engine import Rule, RuleEngine

__all__ = ["RuleContext", "RuleResult", "Rule", "RuleEngine"]
