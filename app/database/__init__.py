"""Persistence layer (Phase 11).

SQLite-backed repositories for events, detections, profiles, cameras, alerts,
settings, and reports. Exposes an ``EventSink`` adapter so the event engine
can persist without knowing about SQL. Schema migrations live here too.
Not yet implemented.
"""

from __future__ import annotations
