"""Load user-authored rules from a directory of Python files.

Each ``.py`` file in the rules directory may expose either:
- ``RULES``: an iterable of rule callables, or
- ``register() -> iterable`` returning rule callables.

This lets operators add custom incident logic as plain Python, version-
controlled alongside the project, without touching the core. Files are
imported in isolation; an error in one file is logged and skipped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.core.logging_config import get_logger
from app.rules.engine import Rule

logger = get_logger(__name__)


def load_rules_from_dir(rules_dir: str | Path) -> list[Rule]:
    """Import every ``*.py`` in ``rules_dir`` and collect its rules."""
    directory = Path(rules_dir)
    if not directory.is_dir():
        return []

    rules: list[Rule] = []
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _import_file(path)
        except Exception as exc:  # noqa: BLE001 - bad file shouldn't break others
            logger.error("Failed to import rule file %s: %s", path.name, exc)
            continue

        collected = getattr(module, "RULES", None)
        if collected is None and hasattr(module, "register"):
            try:
                collected = module.register()
            except Exception as exc:  # noqa: BLE001
                logger.error("register() failed in %s: %s", path.name, exc)
                continue
        if not collected:
            continue
        for rule in collected:
            if callable(rule):
                rules.append(rule)
        logger.info("Loaded %d rule(s) from %s", len(list(collected)), path.name)
    return rules


def _import_file(path: Path):
    spec = importlib.util.spec_from_file_location(f"vision_rules_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
