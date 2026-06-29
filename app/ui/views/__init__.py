"""Center content views, one per navigation section.

Each view is a ``ttk.Frame`` subclass (see :class:`base.BaseView`) that the
router swaps into the center region. Views read from ``AppState`` and emit
intent through injected callbacks; they hold no engine references directly.
"""

from __future__ import annotations
