"""Tracking engine (Phase 9).

Associates per-frame detections into persistent tracks (stable IDs across
frames), implementing the core ``Tracker`` interface. Tracking is what lets
the event engine reason about duration ("no helmet for 3 seconds") rather
than isolated frames. Not yet implemented.
"""

from __future__ import annotations
