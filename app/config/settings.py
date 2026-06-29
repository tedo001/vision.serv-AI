"""Typed configuration schema.

Each section of the YAML config maps to a frozen dataclass. ``AppConfig.from_dict``
performs construction *and* validation, raising ``ConfigValidationError`` with
a precise message on bad input. Keeping the schema as code (rather than ad-hoc
dict access) gives us autocomplete, type checking, and a single source of
truth for defaults.

The product name lives here (``AppConfig.product_name``) so the application
can be rebranded purely via configuration, per the product requirement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.exceptions import ConfigValidationError


def _require_range(name: str, value: float, lo: float, hi: float) -> float:
    if not lo <= value <= hi:
        raise ConfigValidationError(
            f"{name} must be between {lo} and {hi}, got {value}"
        )
    return value


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "logs"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5
    console: bool = True

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LoggingConfig":
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = str(data.get("level", "INFO")).upper()
        if level not in valid_levels:
            raise ConfigValidationError(
                f"logging.level must be one of {sorted(valid_levels)}, got {level!r}"
            )
        return LoggingConfig(
            level=level,
            log_dir=str(data.get("log_dir", "logs")),
            max_bytes=int(data.get("max_bytes", 5 * 1024 * 1024)),
            backup_count=int(data.get("backup_count", 5)),
            console=bool(data.get("console", True)),
        )


@dataclass(frozen=True, slots=True)
class UIConfig:
    theme: str = "clam"
    window_title: str = "AI Vision Platform"
    width: int = 1440
    height: int = 900

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "UIConfig":
        return UIConfig(
            theme=str(data.get("theme", "clam")),
            window_title=str(data.get("window_title", "AI Vision Platform")),
            width=int(data.get("width", 1440)),
            height=int(data.get("height", 900)),
        )


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Global inference defaults; profiles/plugins may override per-module.

    ``active_model`` is the selected YOLO backbone key (see
    :data:`app.detection.model_catalog.MODELS`). ``enabled`` gates whether the
    detection engine runs the model at all. The model *key* is validated at the
    detection layer (not here) to keep the config layer free of detection
    dependencies.
    """

    confidence: float = 0.45
    iou: float = 0.50
    device: str = "auto"  # "auto" | "cpu" | "cuda" | "cuda:0" ...
    model_dir: str = "assets/models"
    active_model: str = "yolo26n"
    enabled: bool = False

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DetectionConfig":
        return DetectionConfig(
            confidence=_require_range(
                "detection.confidence", float(data.get("confidence", 0.45)), 0.0, 1.0
            ),
            iou=_require_range(
                "detection.iou", float(data.get("iou", 0.50)), 0.0, 1.0
            ),
            device=str(data.get("device", "auto")),
            model_dir=str(data.get("model_dir", "assets/models")),
            active_model=str(data.get("active_model", "yolo26n")),
            enabled=bool(data.get("enabled", False)),
        )


@dataclass(frozen=True, slots=True)
class CameraDefaults:
    reconnect_seconds: float = 5.0
    target_fps: int = 25
    buffer_size: int = 1  # low latency: keep only the freshest frame
    width: int = 1280     # requested capture width (0 = camera default)
    height: int = 720     # requested capture height (0 = camera default)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CameraDefaults":
        return CameraDefaults(
            reconnect_seconds=float(data.get("reconnect_seconds", 5.0)),
            target_fps=int(data.get("target_fps", 25)),
            buffer_size=int(data.get("buffer_size", 1)),
            width=int(data.get("width", 1280)),
            height=int(data.get("height", 720)),
        )


@dataclass(frozen=True, slots=True)
class AlertConfig:
    enable_sound: bool = True
    sound_file: str = "assets/sounds/alert.wav"
    min_severity: str = "medium"  # below this, events do not raise alerts

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AlertConfig":
        return AlertConfig(
            enable_sound=bool(data.get("enable_sound", True)),
            sound_file=str(data.get("sound_file", "assets/sounds/alert.wav")),
            min_severity=str(data.get("min_severity", "medium")).lower(),
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Root configuration object passed throughout the application."""

    product_name: str = "AI Vision Platform"
    active_profile: str = "construction"
    database_path: str = "vision_platform.db"
    screenshot_dir: str = "screenshots"
    report_dir: str = "reports"
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    camera: CameraDefaults = field(default_factory=CameraDefaults)
    alert: AlertConfig = field(default_factory=AlertConfig)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppConfig":
        if not isinstance(data, dict):
            raise ConfigValidationError("Top-level config must be a mapping.")
        return AppConfig(
            product_name=str(data.get("product_name", "AI Vision Platform")),
            active_profile=str(data.get("active_profile", "construction")),
            database_path=str(data.get("database_path", "vision_platform.db")),
            screenshot_dir=str(data.get("screenshot_dir", "screenshots")),
            report_dir=str(data.get("report_dir", "reports")),
            logging=LoggingConfig.from_dict(data.get("logging", {}) or {}),
            ui=UIConfig.from_dict(data.get("ui", {}) or {}),
            detection=DetectionConfig.from_dict(data.get("detection", {}) or {}),
            camera=CameraDefaults.from_dict(data.get("camera", {}) or {}),
            alert=AlertConfig.from_dict(data.get("alert", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full config tree to plain dicts for YAML output."""
        return asdict(self)
