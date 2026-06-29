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
        # Build the stat rows once; updates mutate StringVars in place so the
        # high-frequency stats stream (every frame) never rebuilds widgets,
        # which is what caused the panel to flicker/"buffer".
        self._stat_vars = self._build_stat_rows()

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

    # -- stats (built once, updated in place) --------------------------------
    _STAT_ROWS = (
        ("cameras", "Active cameras"),
        ("events", "Events today"),
        ("alerts", "Active alerts"),
        ("dps", "Detections/s"),
    )

    def _build_stat_rows(self) -> dict[str, tk.StringVar]:
        variables: dict[str, tk.StringVar] = {}
        for key, label in self._STAT_ROWS:
            row = ttk.Frame(self._stats_box, style="Sidebar.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, background=PALETTE.sidebar,
                      foreground=PALETTE.text_muted, font=("Segoe UI", 9)).pack(side="left")
            var = tk.StringVar(value="—")
            variables[key] = var
            ttk.Label(row, textvariable=var, background=PALETTE.sidebar,
                      foreground=PALETTE.text, font=("Segoe UI Semibold", 9)).pack(side="right")
        return variables

    def _render_stats(self, stats: DetectionStats) -> None:
        self._stat_vars["cameras"].set(f"{stats.active_cameras}/{stats.total_cameras}")
        self._stat_vars["events"].set(str(stats.events_today))
        self._stat_vars["alerts"].set(str(stats.active_alerts))
        self._stat_vars["dps"].set(f"{stats.detections_per_second:.1f}")

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
