"""Bottom status bar: transient status message + clock.

Binds to ``AppState.status_message`` and ticks a clock. Minimal by design.
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from app.ui.state import AppState


class StatusBar(ttk.Frame):
    def __init__(self, parent: tk.Widget, state: AppState) -> None:
        super().__init__(parent, style="Statusbar.TFrame", padding=(12, 4))
        self._state = state

        self._msg_var = tk.StringVar()
        ttk.Label(self, textvariable=self._msg_var,
                  style="Statusbar.TLabel").pack(side="left")

        self._clock_var = tk.StringVar()
        ttk.Label(self, textvariable=self._clock_var,
                  style="Statusbar.TLabel").pack(side="right")

        state.status_message.subscribe(self._msg_var.set)
        self._tick()

    def _tick(self) -> None:
        self._clock_var.set(time.strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick)
