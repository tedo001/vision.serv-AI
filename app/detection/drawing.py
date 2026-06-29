"""Bounding-box rendering onto frames.

Pure drawing helper kept separate from both capture and inference so any
front-end can reuse it. ``cv2`` is imported lazily so the module imports
without OpenCV present.
"""

from __future__ import annotations

import numpy as np

from app.core.models import Detection

# Distinct BGR colors cycled per class label for visual separation.
_PALETTE_BGR = [
    (59, 130, 246), (34, 197, 94), (239, 68, 68), (245, 158, 11),
    (168, 85, 247), (14, 165, 233), (236, 72, 153), (132, 204, 22),
]


def _color_for(label: str) -> tuple[int, int, int]:
    return _PALETTE_BGR[hash(label) % len(_PALETTE_BGR)]


def draw_detections(image: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """Return a copy of ``image`` with labeled boxes drawn.

    The input is not mutated so the original frame can be reused (e.g. for
    screenshots) independently of the annotated display copy.
    """
    import cv2  # deferred heavy import

    annotated = image.copy()
    for det in detections:
        x1, y1, x2, y2 = (int(det.box.x1), int(det.box.y1),
                          int(det.box.x2), int(det.box.y2))
        color = _color_for(det.label)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        caption = f"{det.label} {det.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, caption, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return annotated
