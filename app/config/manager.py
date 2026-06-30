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
DEFAULT_OVERRIDES_PATH = Path("config/local.yaml")


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``overlay`` onto ``base`` (overlay wins)."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class ConfigManager:
    """Owns loading, validation, and access of application configuration.

    Layering: the committed ``config_path`` (default.yaml) is the documented
    baseline; runtime changes are written to ``overrides_path`` (local.yaml,
    gitignored) and merged on top at load time. This keeps the documented
    template — and its comments — pristine while user edits persist separately.
    When ``overrides_path`` is None, the manager reads and writes a single file
    (used by tests).
    """

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG_PATH,
        *,
        overrides_path: Path | str | None = None,
    ) -> None:
        self._config_path = Path(config_path)
        self._overrides_path = Path(overrides_path) if overrides_path else None
        self._config: AppConfig | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def _save_path(self) -> Path:
        """Where runtime changes are written."""
        return self._overrides_path or self._config_path

    @property
    def config(self) -> AppConfig:
        """Return the loaded config, loading it on first access."""
        if self._config is None:
            self.load()
        assert self._config is not None  # for type checkers
        return self._config

    def load(self) -> AppConfig:
        """Load, merge overrides, and validate config; fall back to defaults."""
        data = self._read_yaml(self._config_path)
        if data is None:
            logger.warning(
                "Config file %s not found; using built-in defaults.",
                self._config_path,
            )
            data = {}

        if self._overrides_path is not None:
            overrides = self._read_yaml(self._overrides_path)
            if overrides:
                data = _deep_merge(data, overrides)
                logger.info("Applied config overrides from %s", self._overrides_path)

        self._config = AppConfig.from_dict(data)
        logger.info(
            "Loaded configuration for product %r (profile=%s)",
            self._config.product_name,
            self._config.active_profile,
        )
        return self._config

    def _read_yaml(self, path: Path) -> dict[str, Any] | None:
        """Read a YAML file to a dict, or None if missing."""
        if not path.exists():
            return None
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"Failed to read/parse config at {path}: {exc}") from exc

    def reload(self) -> AppConfig:
        """Force a re-read from disk (supports future hot-reload)."""
        self._config = None
        return self.load()

    def save(self, config: AppConfig | None = None) -> None:
        """Persist ``config`` (or the loaded one) to the save path.

        Writes to the overrides file when configured, leaving the committed
        default template untouched.
        """
        target = config if config is not None else self.config
        save_path = self._save_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            save_path.write_text(
                yaml.safe_dump(target.to_dict(), sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigError(
                f"Failed to write config to {save_path}: {exc}"
            ) from exc
        self._config = target
        logger.info("Saved configuration to %s", save_path)

    def set_active_profile(self, profile_key: str) -> AppConfig:
        """Persist ``profile_key`` as the active profile."""
        new_config = replace(self.config, active_profile=profile_key)
        self.save(new_config)
        return new_config

    def update_detection(
        self,
        *,
        active_model: str | None = None,
        enabled: bool | None = None,
        confidence: float | None = None,
        iou: float | None = None,
        device: str | None = None,
        enabled_models: tuple[str, ...] | None = None,
        track: bool | None = None,
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
            "device": current.device if device is None else device,
            "model_dir": current.model_dir,
            "active_model": current.active_model if active_model is None else active_model,
            "enabled": current.enabled if enabled is None else enabled,
            "enabled_models": list(
                current.enabled_models if enabled_models is None else enabled_models),
            "track": current.track if track is None else track,
        }
        new_detection: DetectionConfig = DetectionConfig.from_dict(merged)
        new_config = replace(self.config, detection=new_detection)
        self.save(new_config)
        return new_config
