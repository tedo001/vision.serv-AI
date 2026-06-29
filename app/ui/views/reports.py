"""Reports: generate operational reports and list generated files.

Generate writes a real file into the configured ``report_dir`` and refreshes
the list below it. Historical aggregation arrives with the database (Phase 11).
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from app.config.settings import AppConfig
from app.core.logging_config import get_logger
from app.reports.generator import ReportContext, generate_report, list_reports
from app.ui.state import AppState
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)


class ReportsView(BaseView):
    def __init__(self, parent: tk.Widget, state: AppState, config: AppConfig) -> None:
        self._config = config
        super().__init__(parent, state)

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

        ttk.Button(controls, text="Generate", style="Accent.TButton",
                   command=self._on_generate).grid(row=1, column=1)
        ttk.Button(controls, text="Refresh list",
                   command=self._refresh_list).grid(row=1, column=2, padx=(8, 0))

        # Generated files list
        wrap = ttk.Frame(self, style="Surface.TFrame", padding=12)
        wrap.pack(fill="both", expand=True)
        cols = ("name", "modified", "size")
        self._tree = ttk.Treeview(wrap, columns=cols, show="headings", height=12)
        for col, head, width in (("name", "Report", 360),
                                 ("modified", "Generated", 200),
                                 ("size", "Size", 100)):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=width, anchor="w")
        self._tree.pack(fill="both", expand=True)

        self._refresh_list()

    def _on_generate(self) -> None:
        stats = self.state.stats.value
        ctx = ReportContext(
            report_type=self._type.get(),
            product_name=self.state.product_name.value,
            profile=self.state.active_profile.value,
            model=self.state.active_model.value,
            active_cameras=stats.active_cameras,
            total_cameras=stats.total_cameras,
            events_today=stats.events_today,
            active_alerts=stats.active_alerts,
        )
        try:
            path = generate_report(ctx, self._config.report_dir)
        except OSError as exc:
            logger.error("Report generation failed: %s", exc)
            self.state.status_message.set(f"Report failed: {exc}")
            return
        logger.info("Generated report %s", path)
        self.state.status_message.set(f"Report saved: {path.name}")
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._tree.delete(*self._tree.get_children())
        files = list_reports(self._config.report_dir)
        if not files:
            self._tree.insert("", "end", values=("No reports generated yet", "—", "—"))
            return
        for path in files:
            stat = path.stat()
            modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            self._tree.insert("", "end",
                              values=(path.name, modified, f"{stat.st_size} B"))

    def on_show(self) -> None:
        self._refresh_list()
