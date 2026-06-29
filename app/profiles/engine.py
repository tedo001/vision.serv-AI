"""Industry profile engine (Phase 6).

Turns a selected profile into live behaviour. Today it does two concrete
things: (1) makes the active profile the persisted default, and (2) resolves
the set of detection classes a profile cares about so the detection pipeline
can focus on them. As later phases land it will also load per-profile rules,
dashboards, and alert policies — callers depend on this engine, not on the
catalog directly, so that growth doesn't ripple outward.
"""

from __future__ import annotations

from app.core.exceptions import ProfileError
from app.core.logging_config import get_logger
from app.profiles.catalog import get_profile

logger = get_logger(__name__)


def relevant_classes(profile_key: str) -> frozenset[str]:
    """COCO classes the active profile focuses on (empty = no filter)."""
    profile = get_profile(profile_key)
    return frozenset(profile.coco_classes) if profile else frozenset()


class ProfileEngine:
    """Applies profile selection to live state and persisted config."""

    def __init__(self, config_manager, state) -> None:
        self._config_manager = config_manager
        self._state = state

    def apply_profile(self, profile_key: str) -> None:
        """Activate ``profile_key``: update live state and persist it."""
        profile = get_profile(profile_key)
        if profile is None:
            raise ProfileError(f"Unknown industry profile: {profile_key!r}")

        self._state.active_profile.set(profile.key)
        try:
            self._config_manager.set_active_profile(profile.key)
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            logger.error("Failed to persist active profile: %s", exc)

        n = len(profile.coco_classes)
        self._state.status_message.set(
            f"Activated {profile.display_name} — detection focuses on "
            f"{n} object type(s)." if n else
            f"Activated {profile.display_name}.")
        logger.info("Applied profile %s (classes=%s)",
                    profile.key, ", ".join(profile.coco_classes) or "all")

    def clear_profile(self) -> None:
        """Deactivate the current profile (no focus → detect everything)."""
        self._state.active_profile.set("")
        try:
            self._config_manager.set_active_profile("")
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            logger.error("Failed to persist profile deactivation: %s", exc)
        self._state.status_message.set("No profile active — detecting all objects.")
        logger.info("Cleared active profile")

    def toggle_profile(self, profile_key: str) -> None:
        """Activate ``profile_key``, or deactivate it if already active."""
        if self._state.active_profile.value == profile_key:
            self.clear_profile()
        else:
            self.apply_profile(profile_key)

    def relevant_classes(self, profile_key: str | None = None) -> frozenset[str]:
        key = profile_key or self._state.active_profile.value
        return relevant_classes(key)
