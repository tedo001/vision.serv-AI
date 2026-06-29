"""A small, explicit dependency-injection container.

Rationale: a full DI framework would be overkill and would obscure control
flow. But manual wiring scattered across the codebase makes testing painful
and creates hidden global state. This container is the middle ground: a
single composition root registers providers; the rest of the app resolves
dependencies through it. Tests register fakes/mocks against the same keys.

Two provider styles are supported:
- ``register_singleton``: one shared, lazily-created instance.
- ``register_factory``: a fresh instance per ``resolve`` call.

Keys are strings (stable, decoupled from concrete classes), which also lets
configuration/plugins reference services by name.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from app.core.exceptions import (
    ServiceAlreadyRegisteredError,
    ServiceNotRegisteredError,
)

Provider = Callable[["Container"], Any]


class Container:
    """Thread-safe service registry and resolver."""

    def __init__(self) -> None:
        self._factories: dict[str, Provider] = {}
        self._singleton_providers: dict[str, Provider] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = threading.RLock()

    # -- Registration --------------------------------------------------------
    def register_factory(self, key: str, provider: Provider) -> None:
        """Register a provider invoked on every :meth:`resolve`."""
        with self._lock:
            self._ensure_free(key)
            self._factories[key] = provider

    def register_singleton(self, key: str, provider: Provider) -> None:
        """Register a provider invoked at most once; result is cached."""
        with self._lock:
            self._ensure_free(key)
            self._singleton_providers[key] = provider

    def register_instance(self, key: str, instance: Any) -> None:
        """Register an already-constructed object as a singleton."""
        with self._lock:
            self._ensure_free(key)
            self._singletons[key] = instance

    # -- Resolution ----------------------------------------------------------
    def resolve(self, key: str) -> Any:
        """Return the service registered under ``key``.

        Singletons are created lazily on first resolution and cached.
        """
        with self._lock:
            if key in self._singletons:
                return self._singletons[key]
            if key in self._singleton_providers:
                instance = self._singleton_providers[key](self)
                self._singletons[key] = instance
                return instance
            if key in self._factories:
                return self._factories[key](self)
        raise ServiceNotRegisteredError(f"No service registered for key: {key!r}")

    def has(self, key: str) -> bool:
        with self._lock:
            return (
                key in self._singletons
                or key in self._singleton_providers
                or key in self._factories
            )

    def reset(self) -> None:
        """Clear all registrations and cached instances (used in tests)."""
        with self._lock:
            self._factories.clear()
            self._singleton_providers.clear()
            self._singletons.clear()

    # -- Internal ------------------------------------------------------------
    def _ensure_free(self, key: str) -> None:
        if self.has(key):
            raise ServiceAlreadyRegisteredError(
                f"Service already registered for key: {key!r}"
            )
