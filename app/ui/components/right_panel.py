"""Right panel: active events, alerts, and detection statistics.

Always visible alongside the live view. Binds to ``AppState`` lists/counters
and re-renders on change. Pure presentation.
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from app.core.models import Alert, Event
from app.ui.state import AppState, DetectionStats
from app.ui.theme import PALETTE
from app.ui.widgets import Badge


class RightPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, state: AppState, width: int = 300) -> None:
        super().__init__(parent, style="Sidebar.TFrame", width=width, padding=12)
        self.pack_propagate(False)
        self._state = state

        ttk.Label(self, text="Detection Statistics", style="H2.TLabel",
                  background=PALETTE.sidebar).pack(anchor="w")
        self._stats_box = ttk.Frame(self, style="Sidebar.TFrame")
        self._stats_box.pack(fill="x", pady=(8, 16))

        ttk.Label(self, text="Active Alerts", style="H2.TLabel",
                  background=PALETTE.sidebar).pack(anchor="w")
        self._alerts_box = ttk.Frame(self, style="Sidebar.TFrame")
        self._alerts_box.pack(fill="x", pady=(8, 16))

        ttk.Label(self, text="Recent Events", style="H2.TLabel",
                  background=PALETTE.sidebar).pack(anchor="w")
        self._events_box = ttk.Frame(self, style="Sidebar.TFrame")
        self._events_box.pack(fill="both", expand=True, pady=(8, 0))

        state.stats.subscribe(self._render_stats)
        state.alerts.subscribe(self._render_alerts)
        state.events.subscribe(self._render_events)

    # -- renderers -----------------------------------------------------------
    def _render_stats(self, stats: DetectionStats) -> None:
        for w in self._stats_box.winfo_children():
            w.destroy()
        rows = (
            ("Active cameras", f"{stats.active_cameras}/{stats.total_cameras}"),
            ("Events today", str(stats.events_today)),
            ("Active alerts", str(stats.active_alerts)),
            ("Detections/s", f"{stats.detections_per_second:.1f}"),
        )
        for label, value in rows:
            row = ttk.Frame(self._stats_box, style="Sidebar.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, background=PALETTE.sidebar,
                      foreground=PALETTE.text_muted, font=("Segoe UI", 9)).pack(side="left")
            ttk.Label(row, text=value, background=PALETTE.sidebar,
                      foreground=PALETTE.text, font=("Segoe UI Semibold", 9)).pack(side="right")

    def _render_alerts(self, alerts: tuple[Alert, ...]) -> None:
        for w in self._alerts_box.winfo_children():
            w.destroy()
        if not alerts:
            self._empty(self._alerts_box, "No active alerts")
            return
        for alert in alerts[:5]:
            row = ttk.Frame(self._alerts_box, style="Sidebar.TFrame")
            row.pack(fill="x", pady=3)
            Badge(row, alert.event.severity.value.upper(),
                  alert.event.severity.value).pack(side="left", padx=(0, 6))
            ttk.Label(row, text=alert.event.message, background=PALETTE.sidebar,
                      foreground=PALETTE.text, font=("Segoe UI", 9),
                      wraplength=200, justify="left").pack(side="left")

    def _render_events(self, events: tuple[Event, ...]) -> None:
        for w in self._events_box.winfo_children():
            w.destroy()
        if not events:
            self._empty(self._events_box, "No events yet")
            return
        for event in events[:8]:
            row = ttk.Frame(self._events_box, style="Sidebar.TFrame")
            row.pack(fill="x", pady=3)
            when = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
            ttk.Label(row, text=when, background=PALETTE.sidebar,
                      foreground=PALETTE.text_muted, font=("Segoe UI", 8)).pack(anchor="w")
            ttk.Label(row, text=event.message, background=PALETTE.sidebar,
                      foreground=PALETTE.text, font=("Segoe UI", 9),
                      wraplength=260, justify="left").pack(anchor="w")

    def _empty(self, parent: tk.Widget, text: str) -> None:
        ttk.Label(parent, text=text, background=PALETTE.sidebar,
                  foreground=PALETTE.text_muted, font=("Segoe UI", 9)).pack(anchor="w")
