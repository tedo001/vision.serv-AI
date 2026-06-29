"""Domain exception hierarchy.

A single rooted hierarchy lets callers catch broadly (``VisionPlatformError``)
or narrowly (``ConfigError``) without coupling to third-party exception types.
Outer layers translate these into user-facing messages; they never leak
library-specific exceptions (cv2, yaml, sqlite3) across layer boundaries.
"""

from __future__ import annotations


class VisionPlatformError(Exception):
    """Base class for all errors raised by the platform."""


# --- Configuration -----------------------------------------------------------
class ConfigError(VisionPlatformError):
    """Raised when configuration cannot be loaded, parsed, or validated."""


class ConfigValidationError(ConfigError):
    """Raised when a configuration value violates a schema constraint."""


# --- Dependency Injection ----------------------------------------------------
class DependencyError(VisionPlatformError):
    """Base class for service-container resolution failures."""


class ServiceNotRegisteredError(DependencyError):
    """Raised when a requested service has no registered provider."""


class ServiceAlreadyRegisteredError(DependencyError):
    """Raised when registering a service key that is already taken."""


# --- Camera / Capture (Phase 7) ----------------------------------------------
class CameraError(VisionPlatformError):
    """Raised on camera open/read/configuration failures."""


# --- Detection / Inference (Phase 8) -----------------------------------------
class DetectionError(VisionPlatformError):
    """Raised when a detector fails to load a model or run inference."""


class PluginError(VisionPlatformError):
    """Raised when a plugin cannot be discovered, loaded, or initialized."""


# --- Profiles (Phase 6) ------------------------------------------------------
class ProfileError(VisionPlatformError):
    """Raised when an industry profile is missing or malformed."""


# --- Persistence (Phase 11) --------------------------------------------------
class StorageError(VisionPlatformError):
    """Raised on database connection or query failures."""
