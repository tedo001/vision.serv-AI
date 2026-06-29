"""Events: chronological table of confirmed events.

Binds to ``AppState.events``. Phase 10's event engine and Phase 11's database
will populate this; the table contract (columns, formatting) is fixed now.
"""

from __future__ import annotations

import time
from tkinter import ttk

from app.core.models import Event
from app.ui.views.base import BaseView
from app.ui.widgets import section_title


class EventsView(BaseView):
    def build(self) -> None:
        section_title(self, "Events",
                      "Confirmed events across all cameras").pack(anchor="w", fill="x")

        wrap = ttk.Frame(self, style="Surface.TFrame", padding=12)
        wrap.pack(fill="both", expand=True, pady=16)

        cols = ("time", "camera", "type", "severity", "message")
        self._tree = ttk.Treeview(wrap, columns=cols, show="headings")
        for col, head, width in (
            ("time", "Time", 150), ("camera", "Camera", 110),
            ("type", "Type", 150), ("severity", "Severity", 90),
            ("message", "Message", 320),
        ):
            self._tree.heading(col, text=head)
            self._tree.column(col, width=width, anchor="w")
        self._tree.pack(fill="both", expand=True)

        self.state.events.subscribe(self._render)

    def _render(self, events: tuple[Event, ...]) -> None:
        self._tree.delete(*self._tree.get_children())
        if not events:
            self._tree.insert("", "end", values=("—", "—", "No events recorded", "—", "—"))
            return
        for event in events:
            when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event.timestamp))
            self._tree.insert("", "end", values=(
                when, event.camera_id, event.event_type,
                event.severity.value.upper(), event.message,
            ))
