"""Configuration manager.

Loads YAML from disk into a validated :class:`~app.config.settings.AppConfig`.
If the config file is absent, it falls back to built-in defaults and (when
asked) writes a starter file so first-run users get a documented template.

Why a manager class rather than a module-level ``load()`` function: it holds
the resolved config path and the loaded config, supports reloading, and is
trivially registered as a singleton in the DI container. No global state.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from app.config.settings import AppConfig, DetectionConfig
from app.core.exceptions import ConfigError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = Path("config/default.yaml")


class ConfigManager:
    """Owns loading, validation, and access of application configuration."""

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG_PATH) -> None:
        self._config_path = Path(config_path)
        self._config: AppConfig | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def config(self) -> AppConfig:
        """Return the loaded config, loading it on first access."""
        if self._config is None:
            self.load()
        assert self._config is not None  # for type checkers
        return self._config

    def load(self) -> AppConfig:
        """Load and validate config from disk, or fall back to defaults."""
        if not self._config_path.exists():
            logger.warning(
                "Config file %s not found; using built-in defaults.",
                self._config_path,
            )
            self._config = AppConfig()
            return self._config

        try:
            raw = self._config_path.read_text(encoding="utf-8")
            data: Any = yaml.safe_load(raw) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(
                f"Failed to read/parse config at {self._config_path}: {exc}"
            ) from exc

        self._config = AppConfig.from_dict(data)
        logger.info(
            "Loaded configuration for product %r (profile=%s) from %s",
            self._config.product_name,
            self._config.active_profile,
            self._config_path,
        )
        return self._config

    def reload(self) -> AppConfig:
        """Force a re-read from disk (supports future hot-reload)."""
        self._config = None
        return self.load()

    def save(self, config: AppConfig | None = None) -> None:
        """Persist ``config`` (or the loaded one) back to the YAML file."""
        target = config if config is not None else self.config
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._config_path.write_text(
                yaml.safe_dump(target.to_dict(), sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigError(
                f"Failed to write config to {self._config_path}: {exc}"
            ) from exc
        self._config = target
        logger.info("Saved configuration to %s", self._config_path)

    def update_detection(
        self,
        *,
        active_model: str | None = None,
        enabled: bool | None = None,
        confidence: float | None = None,
        iou: float | None = None,
    ) -> AppConfig:
        """Apply detection/model changes and persist them.

        Only provided fields are changed. Returns the new config. Validation
        of numeric ranges is enforced by ``DetectionConfig.from_dict`` via a
        round-trip so invalid values are rejected before they are saved.
        """
        current = self.config.detection
        merged = {
            "confidence": current.confidence if confidence is None else confidence,
            "iou": current.iou if iou is None else iou,
            "device": current.device,
            "model_dir": current.model_dir,
            "active_model": current.active_model if active_model is None else active_model,
            "enabled": current.enabled if enabled is None else enabled,
        }
        new_detection: DetectionConfig = DetectionConfig.from_dict(merged)
        new_config = replace(self.config, detection=new_detection)
        self.save(new_config)
        return new_config
