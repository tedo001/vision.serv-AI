"""AI Modules: the modules enabled by the active profile.

Lists the active profile's modules with enable toggles. The list reacts to
profile changes via ``AppState.active_profile``. Toggling is presentation-only
until the plugin/detection engine (Phase 8) is wired.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.profiles.catalog import get_profile
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title


class ModulesView(BaseView):
    def build(self) -> None:
        header = section_title(self, "AI Modules",
                               "Detection plugins enabled by the active profile")
        header.pack(anchor="w", fill="x")

        self._list = ttk.Frame(self, style="Surface.TFrame", padding=16)
        self._list.pack(fill="both", expand=True, pady=16)

        self.state.active_profile.subscribe(self._render)

    def _render(self, profile_key: str) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        profile = get_profile(profile_key)
        if profile is None:
            msg = ("No active profile — activate one in Industry Profiles to "
                   "load its AI modules." if not profile_key else "Unknown profile")
            ttk.Label(self._list, text=msg, style="SurfaceMuted.TLabel").pack(anchor="w")
            return

        ttk.Label(self._list, text=f"{profile.display_name} — {len(profile.modules)} modules",
                  style="SurfaceMuted.TLabel").pack(anchor="w", pady=(0, 12))

        # Track which modules are enabled (all on by default).
        self._enabled: dict[str, tk.BooleanVar] = {}

        grid = ttk.Frame(self._list, style="Surface.TFrame")
        grid.pack(fill="both", expand=True)
        for i in range(2):
            grid.columnconfigure(i, weight=1)
        for idx, module in enumerate(profile.modules):
            row = ttk.Frame(grid, style="Surface.TFrame")
            row.grid(row=idx // 2, column=idx % 2, sticky="w", padx=8, pady=4)
            var = tk.BooleanVar(value=True)
            self._enabled[module] = var
            ttk.Checkbutton(row, variable=var, takefocus=False,
                            command=lambda m=module: self._on_toggle(m)).pack(side="left")
            ttk.Label(row, text=module, background=PALETTE.surface,
                      foreground=PALETTE.text, font=("Segoe UI", 10)).pack(side="left", padx=6)

    def _on_toggle(self, module: str) -> None:
        on = sum(1 for v in self._enabled.values() if v.get())
        state = "enabled" if self._enabled[module].get() else "disabled"
        self.state.status_message.set(
            f"{module} {state} — {on}/{len(self._enabled)} modules active")
