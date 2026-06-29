"""Configuration manager.

Loads YAML from disk into a validated :class:`~app.config.settings.AppConfig`.
If the config file is absent, it falls back to built-in defaults and (when
asked) writes a starter file so first-run users get a documented template.

Why a manager class rather than a module-level ``load()`` function: it holds
the resolved config path and the loaded config, supports reloading, and is
trivially registered as a singleton in the DI container. No global state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.config.settings import AppConfig
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
