"""Tests for the framework-agnostic UI layer (no GUI toolkit required).

These cover the observable state, navigation model, and profile catalog — the
parts a future non-Tkinter front-end would reuse unchanged.
"""

from __future__ import annotations

from app.profiles.catalog import PROFILES, get_profile
from app.ui.navigation import NAV_ITEMS, NavSection
from app.ui.state import AppState, ConnectionStatus, DetectionStats, Observable


def test_observable_notifies_subscribers() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    obs.subscribe(seen.append)  # immediate -> records 0
    obs.set(5)
    obs.set(9)
    assert seen == [0, 5, 9]


def test_observable_immediate_false_skips_initial() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    obs.subscribe(seen.append, immediate=False)
    obs.set(1)
    assert seen == [1]


def test_observable_unsubscribe_stops_updates() -> None:
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    unsubscribe = obs.subscribe(seen.append, immediate=False)
    obs.set(1)
    unsubscribe()
    obs.set(2)
    assert seen == [1]


def test_observable_skips_notify_on_unchanged_value() -> None:
    """Setting an equal value must not re-fire (prevents stats-panel flicker)."""
    obs: Observable[int] = Observable(0)
    seen: list[int] = []
    obs.subscribe(seen.append, immediate=False)
    obs.set(5)
    obs.set(5)   # unchanged -> no notification
    obs.set(7)
    assert seen == [5, 7]


def test_observable_update_uses_current_value() -> None:
    obs: Observable[int] = Observable(10)
    obs.update(lambda v: v + 5)
    assert obs.value == 15


def test_app_state_from_config_seeds_values() -> None:
    state = AppState.from_config(product_name="Acme", active_profile="retail")
    assert state.product_name.value == "Acme"
    assert state.active_profile.value == "retail"
    assert state.camera_status.value is ConnectionStatus.OFFLINE
    assert isinstance(state.stats.value, DetectionStats)


def test_nav_items_unique_and_cover_all_sections() -> None:
    sections = [item.section for item in NAV_ITEMS]
    assert len(sections) == len(set(sections))  # no duplicates
    assert set(sections) == set(NavSection)      # every section is navigable


def test_profile_catalog_has_seven_verticals() -> None:
    assert len(PROFILES) == 7
    assert get_profile("CONSTRUCTION") is PROFILES["construction"]
    assert get_profile("missing") is None


def test_every_profile_defines_modules() -> None:
    for profile in PROFILES.values():
        assert profile.modules, f"{profile.key} has no modules"
        assert profile.display_name
