"""Tests for the DI container."""

from __future__ import annotations

import pytest

from app.core.container import Container
from app.core.exceptions import (
    ServiceAlreadyRegisteredError,
    ServiceNotRegisteredError,
)


def test_register_instance_and_resolve() -> None:
    container = Container()
    sentinel = object()
    container.register_instance("svc", sentinel)
    assert container.resolve("svc") is sentinel


def test_singleton_is_created_once() -> None:
    container = Container()
    calls = {"n": 0}

    def provider(_c: Container) -> object:
        calls["n"] += 1
        return object()

    container.register_singleton("svc", provider)
    first = container.resolve("svc")
    second = container.resolve("svc")
    assert first is second
    assert calls["n"] == 1


def test_factory_creates_new_each_time() -> None:
    container = Container()
    container.register_factory("svc", lambda _c: object())
    assert container.resolve("svc") is not container.resolve("svc")


def test_resolve_unknown_raises() -> None:
    container = Container()
    with pytest.raises(ServiceNotRegisteredError):
        container.resolve("missing")


def test_duplicate_registration_raises() -> None:
    container = Container()
    container.register_instance("svc", object())
    with pytest.raises(ServiceAlreadyRegisteredError):
        container.register_factory("svc", lambda _c: object())


def test_dependencies_resolve_through_container() -> None:
    container = Container()
    container.register_instance("dep", 21)
    container.register_factory("svc", lambda c: c.resolve("dep") * 2)
    assert container.resolve("svc") == 42
