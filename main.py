"""Application entry point / composition root.

This is the *only* place that knows how the pieces fit together. It builds the
DI container, loads configuration, initializes logging from that config, and
(in later phases) constructs the camera manager, detection/tracking/event
engines, alert system, database, and UI, then hands control to the UI loop.

Keeping all wiring here -- rather than scattered constructors across the
codebase -- is the Clean Architecture "composition root" pattern: dependencies
are assembled at the outermost edge and injected inward.

Run:
    python main.py
"""

from __future__ import annotations

import sys

from app import __version__
from app.config.manager import ConfigManager
from app.core.container import Container
from app.core.logging_config import configure_logging, get_logger
from app.ui.state import AppState

# DI service keys (stable identifiers, decoupled from concrete classes).
SERVICE_CONFIG_MANAGER = "config_manager"
SERVICE_APP_CONFIG = "app_config"
SERVICE_APP_STATE = "app_state"


def build_container() -> Container:
    """Assemble and return the application's DI container."""
    container = Container()

    config_manager = ConfigManager()
    container.register_instance(SERVICE_CONFIG_MANAGER, config_manager)

    # AppConfig resolves lazily from the manager the first time it's needed.
    container.register_singleton(
        SERVICE_APP_CONFIG,
        lambda c: c.resolve(SERVICE_CONFIG_MANAGER).config,
    )

    # The framework-agnostic presentation state the UI (any UI) binds to.
    container.register_singleton(
        SERVICE_APP_STATE,
        lambda c: AppState.from_config(
            product_name=c.resolve(SERVICE_APP_CONFIG).product_name,
            active_profile=c.resolve(SERVICE_APP_CONFIG).active_profile,
            active_model=c.resolve(SERVICE_APP_CONFIG).detection.active_model,
            model_enabled=c.resolve(SERVICE_APP_CONFIG).detection.enabled,
            confidence=c.resolve(SERVICE_APP_CONFIG).detection.confidence,
            iou=c.resolve(SERVICE_APP_CONFIG).detection.iou,
        ),
    )
    return container


def main(argv: list[str] | None = None) -> int:
    """Boot the platform foundation. Returns a process exit code."""
    container = build_container()
    config = container.resolve(SERVICE_APP_CONFIG)

    configure_logging(
        level=config.logging.level,
        log_dir=config.logging.log_dir,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        console=config.logging.console,
    )
    logger = get_logger(__name__)

    logger.info("=" * 64)
    logger.info("%s  v%s  starting up", config.product_name, __version__)
    logger.info("Active profile : %s", config.active_profile)
    logger.info("Inference device: %s", config.detection.device)
    logger.info("UI theme       : %s", config.ui.theme)
    logger.info("=" * 64)

    # Launch the Tkinter desktop UI. Imported lazily so the foundation (and
    # the test suite) remain usable on headless hosts that lack Tkinter.
    try:
        from app.ui.app import VisionApp
    except ModuleNotFoundError as exc:  # tkinter not installed in this build
        logger.error(
            "Tkinter is unavailable (%s). Install it (e.g. 'apt install "
            "python3-tk') and run on a machine with a display.", exc,
        )
        return 1

    try:
        app = VisionApp(container)
    except Exception as exc:  # tk.TclError on headless: no $DISPLAY
        logger.error(
            "Could not open a window (%s). A graphical display is required to "
            "run the desktop UI.", exc,
        )
        return 1

    return app.run()


if __name__ == "__main__":
    sys.exit(main())
