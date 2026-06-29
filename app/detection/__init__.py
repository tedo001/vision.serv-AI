"""Detection engine (Phase 8).

Orchestrates the AI modules enabled by the active profile: dispatches frames
to ``DetectorPlugin`` instances, aggregates their detections, and applies
global confidence/IoU policy. Wraps the YOLO backbone behind the core
interface so the model can be swapped without touching callers.
Not yet implemented.
"""

from __future__ import annotations
