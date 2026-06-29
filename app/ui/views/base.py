"""Base class for center views."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.state import AppState


class BaseView(ttk.Frame):
    """Common scaffolding for a center view.

    Subclasses build their widgets in ``build()``. ``on_show`` is called each
    time the view becomes visible (useful to refresh data lazily).
    """

    def __init__(self, parent: tk.Widget, state: AppState) -> None:
        super().__init__(parent, padding=20)
        self.state = state
        self.build()

    def build(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def on_show(self) -> None:
        """Hook invoked when the view is navigated to. Optional override."""
