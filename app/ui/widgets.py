"""Small reusable ttk widget helpers.

Keeps view code declarative: views compose ``Card`` / ``StatCard`` /
``section_title`` instead of repeating frame + label boilerplate and style
names. Centralizing these also means a styling change propagates everywhere.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from app.ui.theme import PALETTE


def section_title(parent: tk.Widget, text: str, subtitle: str = "") -> ttk.Frame:
    """A page heading with an optional subtitle."""
    frame = ttk.Frame(parent)
    ttk.Label(frame, text=text, style="Title.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(frame, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
    return frame


class Card(ttk.Frame):
    """A rounded-look surface panel with an optional title."""

    def __init__(self, parent: tk.Widget, title: str = "", **kwargs) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=16, **kwargs)
        self.body = self
        if title:
            ttk.Label(self, text=title, style="H2.TLabel",
                      background=PALETTE.surface).pack(anchor="w", pady=(0, 10))
            self.body = ttk.Frame(self, style="Surface.TFrame")
            self.body.pack(fill="both", expand=True)


class StatCard(ttk.Frame):
    """A KPI tile: a big number with a caption. The number is updatable."""

    def __init__(self, parent: tk.Widget, caption: str, value: str = "0") -> None:
        super().__init__(parent, style="Surface.TFrame", padding=16)
        self._value_var = tk.StringVar(value=value)
        ttk.Label(self, textvariable=self._value_var, style="Stat.TLabel").pack(anchor="w")
        ttk.Label(self, text=caption, style="SurfaceMuted.TLabel").pack(anchor="w")

    def set_value(self, value: str) -> None:
        self._value_var.set(value)


class Badge(ttk.Label):
    """A small colored status pill (online/offline/severity)."""

    _COLORS = {
        "online": PALETTE.success,
        "offline": PALETTE.danger,
        "connecting": PALETTE.warning,
        "unknown": PALETTE.text_muted,
        "critical": PALETTE.danger,
        "high": PALETTE.danger,
        "medium": PALETTE.warning,
        "low": PALETTE.accent,
        "info": PALETTE.text_muted,
    }

    def __init__(self, parent: tk.Widget, text: str, kind: str = "unknown",
                 background: Optional[str] = None) -> None:
        color = self._COLORS.get(kind.lower(), PALETTE.text_muted)
        super().__init__(parent, text=f" {text} ", foreground=PALETTE.accent_text,
                         background=color, font=("Segoe UI Semibold", 9))
