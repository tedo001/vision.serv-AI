"""Cameras: list configured sources and add new ones.

Supports the four source types (USB / RTSP / IP / File). The add form is UI
scaffolding for now; Phase 7's CameraManager will consume these definitions to
open real capture threads. No capture logic lives here.
"""

from __future__ import annotations

from tkinter import ttk

from app.core.logging_config import get_logger
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)


class CamerasView(BaseView):
    def build(self) -> None:
        section_title(self, "Cameras",
                      "Connect USB, RTSP, IP, or local video sources").pack(
            anchor="w", fill="x")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=16)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        # --- camera table ---------------------------------------------------
        table_wrap = ttk.Frame(body, style="Surface.TFrame", padding=12)
        table_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        cols = ("name", "type", "source", "status")
        self._tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=12)
        for col, head, width in (
            ("name", "Name", 140), ("type", "Type", 70),
            ("source", "Source", 200), ("status", "Status", 90),
        ):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=width, anchor="w")
        self._tree.pack(fill="both", expand=True)
        self._empty_row()

        # --- add form -------------------------------------------------------
        form = ttk.Frame(body, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="nsew")
        ttk.Label(form, text="Add Camera", style="H2.TLabel",
                  background="#1a2129").pack(anchor="w", pady=(0, 12))

        self._name = self._field(form, "Name")
        self._type = ttk.Combobox(form, values=["USB", "RTSP", "IP", "File"],
                                  state="readonly")
        self._type.set("RTSP")
        ttk.Label(form, text="Type", style="SurfaceMuted.TLabel").pack(anchor="w")
        self._type.pack(fill="x", pady=(0, 8))
        self._source = self._field(form, "Source (URL / index / path)")

        ttk.Button(form, text="Add Camera", style="Accent.TButton",
                   command=self._on_add).pack(anchor="w", pady=(8, 0))

    def _field(self, parent: ttk.Frame, label: str) -> ttk.Entry:
        ttk.Label(parent, text=label, style="SurfaceMuted.TLabel").pack(anchor="w")
        entry = ttk.Entry(parent)
        entry.pack(fill="x", pady=(0, 8))
        return entry

    def _empty_row(self) -> None:
        self._tree.insert("", "end", values=("No cameras configured", "—", "—", "—"))

    def _on_add(self) -> None:
        name = self._name.get().strip() or "Unnamed"
        cam_type = self._type.get()
        source = self._source.get().strip()
        # Phase 7 will validate and open the source; for now record intent.
        logger.info("Add-camera requested: name=%s type=%s source=%s",
                    name, cam_type, source)
        self.state.status_message.set(
            f"Camera '{name}' queued ({cam_type}). Capture arrives in Phase 7.")
