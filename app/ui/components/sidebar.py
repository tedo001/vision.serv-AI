"""Left sidebar navigation.

Renders the section list from :data:`app.ui.navigation.NAV_ITEMS` and invokes
a callback when a section is chosen. The active button is restyled. The
sidebar knows nothing about what each view contains.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from app.ui.navigation import NAV_ITEMS, NavSection
from app.ui.theme import PALETTE


class Sidebar(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[NavSection], None],
        width: int = 210,
    ) -> None:
        super().__init__(parent, style="Sidebar.TFrame", width=width)
        self.pack_propagate(False)
        self._on_select = on_select
        self._buttons: dict[NavSection, ttk.Button] = {}
        self._active: NavSection | None = None

        for item in NAV_ITEMS:
            btn = ttk.Button(
                self,
                text=f"  {item.symbol}   {item.title}",
                style="Sidebar.TButton",
                command=lambda s=item.section: self._select(s),
                takefocus=False,
            )
            btn.pack(fill="x", padx=8, pady=1)
            self._buttons[item.section] = btn

        # Footer pinned to bottom
        footer = ttk.Frame(self, style="Sidebar.TFrame")
        footer.pack(side="bottom", fill="x", pady=12)
        ttk.Label(footer, text="v0.1.0", background=PALETTE.sidebar,
                  foreground=PALETTE.text_muted, font=("Segoe UI", 8)).pack()

    def _select(self, section: NavSection) -> None:
        self.set_active(section)
        self._on_select(section)

    def set_active(self, section: NavSection) -> None:
        """Restyle buttons so ``section`` reads as selected."""
        if self._active is not None:
            self._buttons[self._active].configure(style="Sidebar.TButton")
        self._buttons[section].configure(style="SidebarActive.TButton")
        self._active = section
