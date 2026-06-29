"""Core layer: domain models, interfaces, exceptions, DI container, logging.

This layer is the architectural center of the application. It has **no
dependencies** on outer layers (UI, camera I/O, concrete detectors,
database). Everything else depends inward on the abstractions defined here.

This is the Dependency Rule of Clean Architecture: source-code dependencies
point only inward, toward higher-level policy.
"""

from __future__ import annotations
