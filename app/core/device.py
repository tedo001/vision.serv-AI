"""Compute device (CPU/GPU) resolution and reporting.

Centralizes the "auto -> cuda or cpu" decision and GPU naming so the UI and
detectors agree. ``torch`` is imported lazily and failures degrade to CPU:
the platform must run without a GPU (or without torch installed at all).
"""

from __future__ import annotations

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def cuda_available() -> bool:
    """True if a CUDA GPU is usable. Never raises."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:  # torch missing or broken install
        return False


def resolve_device(preference: str) -> str:
    """Resolve a device preference into a concrete device string.

    "auto" -> "cuda" when available else "cpu"; explicit values pass through.
    """
    pref = (preference or "auto").lower()
    if pref == "auto":
        return "cuda" if cuda_available() else "cpu"
    return pref


def gpu_info() -> tuple[bool, str]:
    """Return (gpu_available, display_name). Falls back to (False, "CPU")."""
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
    except Exception:
        pass
    return False, "CPU"
