"""The Tkinter application shell and view router.

Assembles the persistent chrome (top nav, sidebar, right panel, status bar)
around a swappable center region, and routes navigation to lazily-built views.

This class is the UI-layer composition point. It receives the DI container
from the application's composition root (``main.py``) and pulls what it needs
(config, app state) through it — it never constructs engines itself. Swapping
to a different front-end means replacing this file and the widget layer while
keeping ``AppState``, the navigation model, and the backend services intact.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from app.config.settings import AppConfig
from app.core.container import Container
from app.core.logging_config import get_logger
from app.ui.components.right_panel import RightPanel
from app.ui.components.sidebar import Sidebar
from app.ui.components.status_bar import StatusBar
from app.ui.components.top_nav import TopNav
from app.ui.navigation import NavSection
from app.ui.state import AppState, ConnectionStatus
from app.ui.theme import apply_theme
from app.ui.views.about import AboutView
from app.ui.views.base import BaseView
from app.ui.views.cameras import CamerasView
from app.ui.views.dashboard import DashboardView
from app.ui.views.events import EventsView
from app.ui.views.logs import LogsView
from app.ui.views.modules import ModulesView
from app.ui.views.profiles import ProfilesView
from app.ui.views.reports import ReportsView
from app.ui.views.settings import SettingsView

logger = get_logger(__name__)

# Service keys (mirror main.py to avoid a circular import).
SERVICE_APP_CONFIG = "app_config"
SERVICE_APP_STATE = "app_state"

ViewFactory = Callable[[tk.Widget], BaseView]


class VisionApp:
    """Owns the Tk root and the lifecycle of the desktop UI."""

    def __init__(self, container: Container) -> None:
        self._container = container
        self._config: AppConfig = container.resolve(SERVICE_APP_CONFIG)
        self._state: AppState = container.resolve(SERVICE_APP_STATE)

        self._root = tk.Tk()
        self._root.title(self._config.ui.window_title)
        self._root.geometry(f"{self._config.ui.width}x{self._config.ui.height}")
        self._root.minsize(1100, 720)
        apply_theme(self._root, base_theme=self._config.ui.theme)

        self._views: dict[NavSection, BaseView] = {}
        self._factories: dict[NavSection, ViewFactory] = {}
        self._current: NavSection | None = None

        self._build_layout()
        self._register_views()
        self._show(NavSection.DASHBOARD)
        self._state.status_message.set(
            f"{self._config.product_name} ready — select a profile to begin."
        )

    # -- layout --------------------------------------------------------------
    def _build_layout(self) -> None:
        root = self._root
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

        TopNav(root, self._state).grid(row=0, column=0, sticky="ew")

        body = ttk.Frame(root)
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self._sidebar = Sidebar(body, on_select=self._show)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        self._center = ttk.Frame(body)
        self._center.grid(row=0, column=1, sticky="nsew")
        self._center.rowconfigure(0, weight=1)
        self._center.columnconfigure(0, weight=1)

        RightPanel(body, self._state).grid(row=0, column=2, sticky="ns")

        StatusBar(root, self._state).grid(row=2, column=0, sticky="ew")

    def _register_views(self) -> None:
        state = self._state
        log_path = Path(self._config.logging.log_dir) / "vision_platform.log"
        self._factories = {
            NavSection.DASHBOARD: lambda p: DashboardView(p, state),
            NavSection.PROFILES: lambda p: ProfilesView(p, state),
            NavSection.CAMERAS: lambda p: CamerasView(p, state),
            NavSection.MODULES: lambda p: ModulesView(p, state),
            NavSection.EVENTS: lambda p: EventsView(p, state),
            NavSection.REPORTS: lambda p: ReportsView(p, state),
            NavSection.SETTINGS: lambda p: SettingsView(p, state, self._config),
            NavSection.LOGS: lambda p: LogsView(p, state, log_path),
            NavSection.ABOUT: lambda p: AboutView(p, state),
        }

    # -- routing -------------------------------------------------------------
    def _show(self, section: NavSection) -> None:
        if section == self._current:
            return
        if self._current is not None:
            self._views[self._current].grid_remove()

        view = self._views.get(section)
        if view is None:  # lazy build on first visit
            view = self._factories[section](self._center)
            view.grid(row=0, column=0, sticky="nsew")
            self._views[section] = view

        view.grid()
        view.on_show()
        self._sidebar.set_active(section)
        self._current = section
        logger.debug("Navigated to %s", section.value)

    # -- lifecycle -----------------------------------------------------------
    def run(self) -> int:
        logger.info("Entering Tkinter main loop")
        try:
            self._root.mainloop()
        except KeyboardInterrupt:  # graceful Ctrl-C
            logger.info("Interrupted; shutting down UI")
            self._root.destroy()
        return 0
