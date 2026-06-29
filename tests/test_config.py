"""Tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config.manager import ConfigManager
from app.config.settings import AppConfig
from app.core.exceptions import ConfigError, ConfigValidationError


def test_defaults_when_file_missing(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "does_not_exist.yaml")
    config = manager.load()
    assert isinstance(config, AppConfig)
    assert config.product_name == "AI Vision Platform"
    assert config.detection.confidence == 0.45


def test_load_valid_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "product_name: Acme Vision\n"
        "active_profile: warehouse\n"
        "detection:\n"
        "  confidence: 0.7\n"
        "  iou: 0.3\n",
        encoding="utf-8",
    )
    config = ConfigManager(cfg_file).load()
    assert config.product_name == "Acme Vision"
    assert config.active_profile == "warehouse"
    assert config.detection.confidence == 0.7
    assert config.detection.iou == 0.3


def test_out_of_range_confidence_rejected(tmp_path: Path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("detection:\n  confidence: 1.5\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        ConfigManager(cfg_file).load()


def test_invalid_log_level_rejected(tmp_path: Path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("logging:\n  level: CHATTY\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        ConfigManager(cfg_file).load()


def test_malformed_yaml_raises_config_error(tmp_path: Path) -> None:
    cfg_file = tmp_path / "broken.yaml"
    cfg_file.write_text("product_name: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        ConfigManager(cfg_file).load()


def test_overrides_layer_over_default_and_keep_template_clean(tmp_path: Path) -> None:
    base = tmp_path / "default.yaml"
    overrides = tmp_path / "local.yaml"
    base.write_text(
        "product_name: Base\nactive_profile: construction\n"
        "detection:\n  confidence: 0.45\n  active_model: yolo26n\n",
        encoding="utf-8",
    )
    manager = ConfigManager(base, overrides_path=overrides)

    # Saving a change writes ONLY to the overrides file; base stays untouched.
    manager.update_detection(active_model="yolo26x", confidence=0.7)
    assert "yolo26x" not in base.read_text(encoding="utf-8")
    assert overrides.exists()

    # A fresh manager merges overrides over the base.
    merged = ConfigManager(base, overrides_path=overrides).load()
    assert merged.detection.active_model == "yolo26x"
    assert merged.detection.confidence == 0.7
    assert merged.product_name == "Base"  # untouched key comes from base


def test_set_active_profile_persists_to_overrides(tmp_path: Path) -> None:
    base = tmp_path / "default.yaml"
    base.write_text("active_profile: construction\n", encoding="utf-8")
    overrides = tmp_path / "local.yaml"
    ConfigManager(base, overrides_path=overrides).set_active_profile("office")
    assert ConfigManager(base, overrides_path=overrides).load().active_profile == "office"
    assert "office" not in base.read_text(encoding="utf-8")


def test_product_name_is_configurable(tmp_path: Path) -> None:
    """The product must be rebrandable via config alone."""
    cfg_file = tmp_path / "brand.yaml"
    cfg_file.write_text("product_name: SiteGuard AI\n", encoding="utf-8")
    assert ConfigManager(cfg_file).load().product_name == "SiteGuard AI"
