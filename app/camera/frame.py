"""Concrete frame type satisfying the core ``Frame`` protocol."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class FrameData:
    """A captured frame plus attribution metadata.

    Implements :class:`app.core.interfaces.Frame` structurally. The image is a
    BGR ``np.ndarray`` (OpenCV's native layout); converters handle RGB at the
    presentation edge.
    """

    image: np.ndarray
    camera_id: str
    frame_index: int
    timestamp: float = field(default_factory=time.time)
