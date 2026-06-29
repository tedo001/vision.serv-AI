"""Configuration layer (Phase 3).

Loads, validates, and exposes application settings from YAML as typed,
immutable dataclasses (see :mod:`app.config.settings`). No other layer reads
YAML directly — they depend on the typed ``AppConfig`` object, which means a
malformed config fails fast at startup with a clear error rather than
producing ``KeyError`` deep inside the detection loop.
"""

from __future__ import annotations

from app.config.manager import ConfigManager
from app.config.settings import (
    AppConfig,
    AlertConfig,
    CameraDefaults,
    DetectionConfig,
    LoggingConfig,
    UIConfig,
)

__all__ = [
    "ConfigManager",
    "AppConfig",
    "AlertConfig",
    "CameraDefaults",
    "DetectionConfig",
    "LoggingConfig",
    "UIConfig",
]
