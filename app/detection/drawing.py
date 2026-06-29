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


# COCO-17 skeleton edges (pairs of keypoint indices).
_SKELETON = [
    (5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4),
    (0, 5), (0, 6),
]
_MIN_JOINT_CONF = 0.3


def _draw_skeleton(cv2, image: np.ndarray, keypoints, color: tuple[int, int, int]) -> None:
    pts = [(int(x), int(y), c) for x, y, c in keypoints]
    for a, b in _SKELETON:
        if a < len(pts) and b < len(pts) and pts[a][2] > _MIN_JOINT_CONF and pts[b][2] > _MIN_JOINT_CONF:
            cv2.line(image, pts[a][:2], pts[b][:2], color, 2)
    for x, y, c in pts:
        if c > _MIN_JOINT_CONF:
            cv2.circle(image, (x, y), 3, (255, 255, 255), -1)


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
        # Highlight action detections (e.g. falls) in red regardless of label.
        color = (0, 0, 255) if det.label in ("fall", "fighting") else _color_for(det.label)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        if det.keypoints:
            _draw_skeleton(cv2, annotated, det.keypoints, color)
        caption = f"{det.label} {det.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, caption, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return annotated
