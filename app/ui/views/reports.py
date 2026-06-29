"""Reports: generate and review operational reports.

Scaffolding for Phase 12. Date range + type selector + generate action; the
actual aggregation/export will be implemented against the database layer.
"""

from __future__ import annotations

from tkinter import ttk

from app.core.logging_config import get_logger
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)


class ReportsView(BaseView):
    def build(self) -> None:
        section_title(self, "Reports",
                      "Generate safety, attendance, and analytics reports").pack(
            anchor="w", fill="x")

        controls = ttk.Frame(self, style="Surface.TFrame", padding=16)
        controls.pack(fill="x", pady=16)

        ttk.Label(controls, text="Report type", style="SurfaceMuted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8))
        self._type = ttk.Combobox(controls, state="readonly", width=24, values=[
            "Safety Compliance", "Attendance", "Events Summary",
            "Occupancy", "Productivity",
        ])
        self._type.set("Safety Compliance")
        self._type.grid(row=1, column=0, padx=(0, 12))

        ttk.Label(controls, text="From (YYYY-MM-DD)", style="SurfaceMuted.TLabel").grid(
            row=0, column=1, sticky="w")
        self._from = ttk.Entry(controls, width=16)
        self._from.grid(row=1, column=1, padx=(0, 12))

        ttk.Label(controls, text="To (YYYY-MM-DD)", style="SurfaceMuted.TLabel").grid(
            row=0, column=2, sticky="w")
        self._to = ttk.Entry(controls, width=16)
        self._to.grid(row=1, column=2, padx=(0, 12))

        ttk.Button(controls, text="Generate", style="Accent.TButton",
                   command=self._on_generate).grid(row=1, column=3)

        ttk.Label(self, text="Generated reports will be listed here.",
                  style="Muted.TLabel").pack(anchor="w")

    def _on_generate(self) -> None:
        logger.info("Report requested: type=%s from=%s to=%s",
                    self._type.get(), self._from.get(), self._to.get())
        self.state.status_message.set(
            f"'{self._type.get()}' report queued. Reporting arrives in Phase 12.")
