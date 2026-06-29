"""Dashboard: KPI tiles + the live video region placeholder.

The center video canvas lives here. Until the camera/detection engines exist
(Phases 7-8) it shows a placeholder; the surrounding layout (bounding-box
overlay target, inference info strip) is already in place.
"""

from __future__ import annotations

from tkinter import ttk

from app.ui.state import DetectionStats
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import StatCard, section_title


class DashboardView(BaseView):
    def build(self) -> None:
        section_title(self, "Dashboard",
                      "Live operational overview for the active profile").pack(
            anchor="w", fill="x")

        # KPI row
        kpis = ttk.Frame(self)
        kpis.pack(fill="x", pady=16)
        self._cards: dict[str, StatCard] = {}
        for key, caption in (
            ("cameras", "Active Cameras"),
            ("events", "Events Today"),
            ("alerts", "Active Alerts"),
            ("fps", "Detections / s"),
        ):
            card = StatCard(kpis, caption)
            card.pack(side="left", expand=True, fill="x", padx=(0, 12))
            self._cards[key] = card

        # Live video region
        video_wrap = ttk.Frame(self, style="Surface.TFrame", padding=2)
        video_wrap.pack(fill="both", expand=True)
        self._canvas = ttk.Label(
            video_wrap,
            text="◉  Live video appears here\n\nConnect a camera and start a "
                 "profile to begin real-time detection.",
            style="SurfaceMuted.TLabel", anchor="center", justify="center",
        )
        self._canvas.pack(fill="both", expand=True)

        # Inference info strip
        info = ttk.Frame(self, style="Surface.TFrame", padding=(12, 8))
        info.pack(fill="x", pady=(12, 0))
        self._info_var = ttk.Label(info, text="Inference: idle   •   Model: not loaded   •   Tracker: idle",
                                   style="SurfaceMuted.TLabel")
        self._info_var.pack(anchor="w")

        self.state.stats.subscribe(self._render_stats)
        self.state.fps.subscribe(lambda v: self._cards["fps"].set_value(f"{v:.1f}"))

    def _render_stats(self, stats: DetectionStats) -> None:
        self._cards["cameras"].set_value(f"{stats.active_cameras}/{stats.total_cameras}")
        self._cards["events"].set_value(str(stats.events_today))
        self._cards["alerts"].set_value(str(stats.active_alerts))
