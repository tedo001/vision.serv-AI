"""Settings: read-only view of the resolved application configuration.

Displays the loaded ``AppConfig`` grouped by section. Editing + persistence is
a later iteration; surfacing the live config now makes misconfiguration
obvious and documents what's tunable in ``config/default.yaml``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.config.settings import AppConfig
from app.ui.state import AppState
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title


class SettingsView(BaseView):
    def __init__(self, parent: tk.Widget, state: AppState, config: AppConfig) -> None:
        self._config = config
        super().__init__(parent, state)

    def build(self) -> None:
        section_title(self, "Settings",
                      "Resolved configuration (edit config/default.yaml)").pack(
            anchor="w", fill="x")

        c = self._config
        groups = {
            "General": [
                ("Product name", c.product_name),
                ("Active profile", c.active_profile),
                ("Database path", c.database_path),
                ("Screenshot dir", c.screenshot_dir),
                ("Report dir", c.report_dir),
            ],
            "Detection": [
                ("Confidence", c.detection.confidence),
                ("IoU", c.detection.iou),
                ("Device", c.detection.device),
                ("Model dir", c.detection.model_dir),
            ],
            "Camera defaults": [
                ("Reconnect (s)", c.camera.reconnect_seconds),
                ("Target FPS", c.camera.target_fps),
                ("Buffer size", c.camera.buffer_size),
            ],
            "Alerts": [
                ("Sound enabled", c.alert.enable_sound),
                ("Sound file", c.alert.sound_file),
                ("Min severity", c.alert.min_severity),
            ],
            "Logging / UI": [
                ("Log level", c.logging.level),
                ("Theme", c.ui.theme),
                ("Window", f"{c.ui.width}×{c.ui.height}"),
            ],
        }

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, pady=16)
        for i in range(2):
            container.columnconfigure(i, weight=1, uniform="settings")

        for idx, (title, rows) in enumerate(groups.items()):
            card = ttk.Frame(container, style="Surface.TFrame", padding=16)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=8, pady=8)
            ttk.Label(card, text=title, style="H2.TLabel",
                      background=PALETTE.surface).pack(anchor="w", pady=(0, 8))
            for label, value in rows:
                row = ttk.Frame(card, style="Surface.TFrame")
                row.pack(fill="x", pady=2)
                ttk.Label(row, text=label, background=PALETTE.surface,
                          foreground=PALETTE.text_muted, font=("Segoe UI", 9)).pack(side="left")
                ttk.Label(row, text=str(value), background=PALETTE.surface,
                          foreground=PALETTE.text, font=("Segoe UI Semibold", 9)).pack(side="right")
