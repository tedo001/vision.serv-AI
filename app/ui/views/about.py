"""About: product identity, version, and architecture summary."""

from __future__ import annotations

from tkinter import ttk

from app import __version__
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title


class AboutView(BaseView):
    def build(self) -> None:
        section_title(self, "About").pack(anchor="w", fill="x")

        card = ttk.Frame(self, style="Surface.TFrame", padding=24)
        card.pack(fill="x", pady=16)

        ttk.Label(card, text=self.state.product_name.value, style="Title.TLabel",
                  background=PALETTE.surface).pack(anchor="w")
        ttk.Label(card, text=f"Version {__version__}", style="SurfaceMuted.TLabel").pack(
            anchor="w", pady=(2, 12))
        ttk.Label(
            card,
            text=("An AI-powered computer vision platform that turns existing "
                  "CCTV cameras into intelligent workplace assistants for safety, "
                  "security, compliance, productivity, and operational monitoring."),
            style="SurfaceMuted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w")

        ttk.Label(
            card,
            text=("Architecture: Clean Architecture · plugin-based AI modules · "
                  "industry profiles · event-driven detection pipeline. The UI "
                  "is a thin presentation layer over a framework-agnostic state "
                  "model, so alternative front-ends can be added without "
                  "touching the core."),
            style="SurfaceMuted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w", pady=(12, 0))
