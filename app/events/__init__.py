"""Event engine (Phase 10).

The confirmation pipeline that turns raw detections into business events:
track -> confirm over a time window -> generate Event -> capture screenshot
-> publish to registered ``EventSink`` consumers (database, alerts, UI,
reports). Decouples "what was detected" from "what we do about it".
Not yet implemented.
"""

from __future__ import annotations
