"""Industry Profiles: pick a vertical to load its module bundle.

Renders profile cards from the declarative catalog. Selecting one updates
``AppState.active_profile``. Phase 6 will wire selection to the profile engine
(loading models, rules, dashboards, alert policies); here it updates state and
status so the rest of the UI reacts.
"""

from __future__ import annotations

import tkinter as tk

from tkinter import ttk

from app.core.logging_config import get_logger
from app.profiles.catalog import PROFILES, IndustryProfile
from app.profiles.engine import ProfileEngine
from app.ui.state import AppState
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)


class ProfilesView(BaseView):
    def __init__(self, parent: tk.Widget, state: AppState, engine: ProfileEngine) -> None:
        self._engine = engine
        super().__init__(parent, state)

    def build(self) -> None:
        section_title(self, "Industry Profiles",
                      "Selecting a profile auto-enables its AI modules, rules, "
                      "dashboard, and alerts").pack(anchor="w", fill="x")

        grid = ttk.Frame(self)
        grid.pack(fill="both", expand=True, pady=16)
        for i in range(3):
            grid.columnconfigure(i, weight=1, uniform="profile")

        self._cards: dict[str, ttk.Frame] = {}
        self._buttons: dict[str, ttk.Button] = {}
        for idx, profile in enumerate(PROFILES.values()):
            card = self._make_card(grid, profile)
            card.grid(row=idx // 3, column=idx % 3, sticky="nsew", padx=8, pady=8)
            self._cards[profile.key] = card

        # Immediate subscription paints initial Active/Deactivate state.
        self.state.active_profile.subscribe(self._highlight)

    def _make_card(self, parent: ttk.Frame, profile: IndustryProfile) -> ttk.Frame:
        card = ttk.Frame(parent, style="Surface.TFrame", padding=16)
        ttk.Label(card, text=profile.display_name, style="H2.TLabel",
                  background=PALETTE.surface).pack(anchor="w")
        ttk.Label(card, text=profile.description, style="SurfaceMuted.TLabel",
                  wraplength=240, justify="left").pack(anchor="w", pady=(4, 8))
        ttk.Label(card, text=f"{len(profile.modules)} AI modules",
                  style="SurfaceMuted.TLabel").pack(anchor="w")
        detectable = ", ".join(profile.coco_classes) or "—"
        ttk.Label(card, text=f"Detects now: {detectable}",
                  style="SurfaceMuted.TLabel", wraplength=240,
                  justify="left").pack(anchor="w", pady=(2, 0))
        btn = ttk.Button(card, text="Activate", style="Accent.TButton",
                         command=lambda k=profile.key: self._select(k))
        btn.pack(anchor="w", pady=(12, 0))
        self._buttons[profile.key] = btn
        return card

    def _select(self, key: str) -> None:
        # Toggle: activating the already-active profile deactivates it. The
        # engine updates state + persistence; buttons/markers refresh via the
        # active_profile subscription below.
        self._engine.toggle_profile(key)

    def _highlight(self, active_key: str) -> None:
        """Reflect the active profile: its button reads 'Deactivate', rest 'Activate'."""
        for key, card in self._cards.items():
            is_active = key == active_key
            button = self._buttons.get(key)
            if button is not None:
                button.configure(
                    text="● Deactivate" if is_active else "Activate",
                    style="Accent.TButton" if is_active else "TButton",
                )
            self._mark_active(card, is_active)

    @staticmethod
    def _mark_active(card: ttk.Frame, active: bool) -> None:
        existing = getattr(card, "_active_marker", None)
        if active and existing is None:
            marker = ttk.Label(card, text="● ACTIVE", background=PALETTE.surface,
                               foreground=PALETTE.success, font=("Segoe UI Semibold", 8))
            marker.pack(anchor="w", pady=(8, 0))
            card._active_marker = marker  # type: ignore[attr-defined]
        elif not active and existing is not None:
            existing.destroy()
            card._active_marker = None  # type: ignore[attr-defined]
