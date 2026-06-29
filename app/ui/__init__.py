"""Presentation layer (Phase 5).

Tkinter/ttk desktop UI: top navigation, left sidebar, center live-video
canvas, right events/alerts panel, and bottom status bar. The UI consumes
domain objects and services through interfaces only -- it contains no AI or
camera logic, per the architectural rule that UI and AI code never mix.
Not yet implemented.
"""

from __future__ import annotations
