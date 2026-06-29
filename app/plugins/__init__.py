"""Plugin system.

Each AI feature (helmet, vest, fall, fire, smoke, restricted_zone, ...) is a
self-contained plugin implementing the core ``DetectorPlugin`` protocol.
Plugins are discovered and registered at runtime; profiles enable a subset.
New plugins are installable without modifying the core application.
Not yet implemented.
"""

from __future__ import annotations
