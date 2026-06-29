"""Camera layer (Phase 7).

Adapters that turn USB / RTSP / IP / file sources into the core
``CameraSource`` and ``Frame`` abstractions (see app/core/interfaces.py),
plus a CameraManager that runs each source on its own capture thread with
reconnect logic. Not yet implemented.
"""

from __future__ import annotations
