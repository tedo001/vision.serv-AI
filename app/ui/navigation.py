"""Navigation model (framework-agnostic).

Defines the sidebar sections once, as data. The Tkinter sidebar renders this
list; a future UI renders the same list. Adding or reordering a section is a
one-line data change, not a UI edit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NavSection(str, Enum):
    DASHBOARD = "dashboard"
    PROFILES = "profiles"
    CAMERAS = "cameras"
    MODULES = "modules"
    EVENTS = "events"
    REPORTS = "reports"
    SETTINGS = "settings"
    LOGS = "logs"
    ABOUT = "about"


@dataclass(frozen=True, slots=True)
class NavItem:
    section: NavSection
    title: str
    symbol: str  # unicode glyph used as a lightweight icon


# Order here is the order shown in the sidebar.
NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem(NavSection.DASHBOARD, "Dashboard", "▦"),     # ▦
    NavItem(NavSection.PROFILES, "Industry Profiles", "▣"),  # ▣
    NavItem(NavSection.CAMERAS, "Cameras", "▶"),         # ▶
    NavItem(NavSection.MODULES, "AI Modules", "⚙"),      # ⚙
    NavItem(NavSection.EVENTS, "Events", "⚠"),           # ⚠
    NavItem(NavSection.REPORTS, "Reports", "▤"),         # ▤
    NavItem(NavSection.SETTINGS, "Settings", "☸"),       # ☸
    NavItem(NavSection.LOGS, "Logs", "☰"),               # ☰
    NavItem(NavSection.ABOUT, "About", "ℹ"),             # ℹ
)
