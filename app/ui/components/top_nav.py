"""Top navigation bar: brand + live status indicators.

Shows logo glyph, product name, current profile, camera/GPU status, and FPS.
Every field binds to ``AppState`` so backend updates appear without the bar
knowing where the data came from.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.profiles.catalog import get_profile
from app.ui.state import AppState, ConnectionStatus
from app.ui.theme import PALETTE
from app.ui.widgets import Badge


class TopNav(ttk.Frame):
    def __init__(self, parent: tk.Widget, state: AppState) -> None:
        super().__init__(parent, style="Topbar.TFrame", padding=(16, 10))
        self._state = state

        # Brand: logo glyph + product name
        brand = ttk.Frame(self, style="Topbar.TFrame")
        brand.pack(side="left")
        ttk.Label(brand, text="◉", style="Brand.TLabel",
                  foreground=PALETTE.accent).pack(side="left", padx=(0, 8))
        self._name_var = tk.StringVar()
        ttk.Label(brand, textvariable=self._name_var,
                  style="Brand.TLabel").pack(side="left")

        # Right cluster: profile, camera, gpu, fps
        right = ttk.Frame(self, style="Topbar.TFrame")
        right.pack(side="right")

        self._profile_var = tk.StringVar()
        self._fps_var = tk.StringVar()
        self._add_metric(right, "Profile", self._profile_var)
        self._cam_badge = self._add_badge(right, "Camera")
        self._gpu_badge = self._add_badge(right, "GPU")
        self._add_metric(right, "FPS", self._fps_var)

        # --- bindings -------------------------------------------------------
        state.product_name.subscribe(self._name_var.set)
        state.active_profile.subscribe(self._on_profile)
        state.fps.subscribe(lambda v: self._fps_var.set(f"{v:.1f}"))
        state.camera_status.subscribe(lambda s: self._set_badge(self._cam_badge, s))
        state.gpu_status.subscribe(lambda s: self._set_badge(self._gpu_badge, s))

    def _add_metric(self, parent: tk.Widget, label: str, var: tk.StringVar) -> None:
        cell = ttk.Frame(parent, style="Topbar.TFrame")
        cell.pack(side="left", padx=14)
        ttk.Label(cell, text=label.upper(), style="TopbarMuted.TLabel").pack(anchor="e")
        ttk.Label(cell, textvariable=var, style="Topbar.TLabel").pack(anchor="e")

    def _add_badge(self, parent: tk.Widget, label: str) -> Badge:
        cell = ttk.Frame(parent, style="Topbar.TFrame")
        cell.pack(side="left", padx=14)
        ttk.Label(cell, text=label.upper(), style="TopbarMuted.TLabel").pack(anchor="e")
        badge = Badge(cell, "—", "unknown")
        badge.pack(anchor="e")
        return badge

    def _set_badge(self, badge: Badge, status: ConnectionStatus) -> None:
        kind = status.value
        text = status.value.capitalize()
        badge.configure(text=f" {text} ", background=Badge._COLORS.get(kind, PALETTE.text_muted))

    def _on_profile(self, key: str) -> None:
        profile = get_profile(key)
        if profile is not None:
            self._profile_var.set(profile.display_name)
        else:
            self._profile_var.set(key.title() if key else "None")
