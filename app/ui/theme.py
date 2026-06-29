"""ttk theming for a modern look without third-party toolkits.

We build on a themeable base ttk theme (``clam`` by default — it accepts the
most style overrides) and apply a cohesive dark palette and named styles.
Components reference these named styles (e.g. ``"Sidebar.TButton"``) rather
than hard-coding colors, so re-skinning is a single-file change here.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Palette:
    """A flat, modern dark palette."""

    bg: str = "#0f1419"          # app background
    surface: str = "#1a2129"     # panels / cards
    surface_alt: str = "#232c36"  # hover / alt rows
    border: str = "#2c3742"
    text: str = "#e6edf3"
    text_muted: str = "#8b98a5"
    accent: str = "#3b82f6"      # primary / selection
    accent_text: str = "#ffffff"
    success: str = "#22c55e"
    warning: str = "#f59e0b"
    danger: str = "#ef4444"
    topbar: str = "#11171d"
    sidebar: str = "#141b22"


PALETTE = Palette()

# Named font tuples kept here so views stay consistent.
FONT_BASE = ("Segoe UI", 10)
FONT_MUTED = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI Semibold", 15)
FONT_H2 = ("Segoe UI Semibold", 12)
FONT_BRAND = ("Segoe UI Semibold", 14)
FONT_STAT = ("Segoe UI Semibold", 22)


def apply_theme(root: tk.Tk, *, base_theme: str = "clam", palette: Palette = PALETTE) -> None:
    """Apply the platform theme to ``root``. Falls back gracefully.

    Args:
        root: The Tk root window.
        base_theme: Preferred ttk base theme; falls back to an available one.
        palette: Color palette to apply.
    """
    style = ttk.Style(root)
    available = style.theme_names()
    chosen = base_theme if base_theme in available else (
        "clam" if "clam" in available else available[0]
    )
    if chosen != base_theme:
        logger.warning(
            "ttk theme %r unavailable; falling back to %r (have: %s)",
            base_theme, chosen, ", ".join(available),
        )
    style.theme_use(chosen)

    root.configure(background=palette.bg)

    # --- Base widgets -------------------------------------------------------
    style.configure(".", background=palette.bg, foreground=palette.text,
                    fieldbackground=palette.surface, font=FONT_BASE,
                    bordercolor=palette.border, focuscolor=palette.accent)
    style.configure("TFrame", background=palette.bg)
    style.configure("TLabel", background=palette.bg, foreground=palette.text)
    style.configure("Muted.TLabel", foreground=palette.text_muted, font=FONT_MUTED)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=palette.text)
    style.configure("H2.TLabel", font=FONT_H2, foreground=palette.text)

    # --- Surfaces / cards ---------------------------------------------------
    style.configure("Surface.TFrame", background=palette.surface,
                    relief="flat", borderwidth=1)
    style.configure("Surface.TLabel", background=palette.surface,
                    foreground=palette.text)
    style.configure("SurfaceMuted.TLabel", background=palette.surface,
                    foreground=palette.text_muted, font=FONT_MUTED)
    style.configure("Stat.TLabel", background=palette.surface,
                    foreground=palette.accent, font=FONT_STAT)

    # --- Top bar ------------------------------------------------------------
    style.configure("Topbar.TFrame", background=palette.topbar)
    style.configure("Topbar.TLabel", background=palette.topbar, foreground=palette.text)
    style.configure("Brand.TLabel", background=palette.topbar,
                    foreground=palette.text, font=FONT_BRAND)
    style.configure("TopbarMuted.TLabel", background=palette.topbar,
                    foreground=palette.text_muted, font=FONT_MUTED)

    # --- Sidebar ------------------------------------------------------------
    style.configure("Sidebar.TFrame", background=palette.sidebar)
    style.configure("Sidebar.TButton", background=palette.sidebar,
                    foreground=palette.text_muted, font=FONT_BASE,
                    borderwidth=0, relief="flat", anchor="w", padding=(16, 10))
    style.map("Sidebar.TButton",
              background=[("active", palette.surface_alt)],
              foreground=[("active", palette.text)])
    style.configure("SidebarActive.TButton", background=palette.surface_alt,
                    foreground=palette.accent, font=("Segoe UI Semibold", 10),
                    borderwidth=0, relief="flat", anchor="w", padding=(16, 10))
    style.map("SidebarActive.TButton",
              background=[("active", palette.surface_alt)],
              foreground=[("active", palette.accent)])

    # --- Buttons ------------------------------------------------------------
    style.configure("Accent.TButton", background=palette.accent,
                    foreground=palette.accent_text, borderwidth=0,
                    padding=(14, 8), font=("Segoe UI Semibold", 10))
    style.map("Accent.TButton",
              background=[("active", "#2f6fd6"), ("disabled", palette.border)])

    # --- Status bar ---------------------------------------------------------
    style.configure("Statusbar.TFrame", background=palette.surface)
    style.configure("Statusbar.TLabel", background=palette.surface,
                    foreground=palette.text_muted, font=FONT_MUTED)

    # --- Treeview (events, cameras tables) ----------------------------------
    style.configure("Treeview", background=palette.surface,
                    fieldbackground=palette.surface, foreground=palette.text,
                    rowheight=26, borderwidth=0)
    style.configure("Treeview.Heading", background=palette.surface_alt,
                    foreground=palette.text_muted, relief="flat",
                    font=("Segoe UI Semibold", 9))
    style.map("Treeview", background=[("selected", palette.accent)],
              foreground=[("selected", palette.accent_text)])

    logger.debug("Applied ttk theme %r with dark palette", chosen)
