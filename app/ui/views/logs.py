"""Logs: tail the application log file.

Reads the rotating log file written by the logging subsystem and shows the
most recent lines. A manual refresh keeps it simple and avoids a background
file-watch thread for now.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

from app.ui.state import AppState
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title


class LogsView(BaseView):
    def __init__(self, parent: tk.Widget, state: AppState, log_path: Path) -> None:
        self._log_path = Path(log_path)
        super().__init__(parent, state)

    def build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        section_title(header, "Logs", str(self._log_path)).pack(side="left")
        ttk.Button(header, text="Refresh", style="Accent.TButton",
                   command=self.on_show).pack(side="right")

        self._text = scrolledtext.ScrolledText(
            self, wrap="none", height=24, background=PALETTE.surface,
            foreground=PALETTE.text, insertbackground=PALETTE.text,
            borderwidth=0, font=("Consolas", 9),
        )
        self._text.pack(fill="both", expand=True, pady=16)
        self.on_show()

    def on_show(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        try:
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
            self._text.insert("1.0", "\n".join(lines[-500:]))
        except OSError:
            self._text.insert("1.0", "Log file not found yet.")
        self._text.see("end")
        self._text.configure(state="disabled")
