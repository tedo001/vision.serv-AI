"""Action detection derived from pose/skeleton keypoints.

Object detection answers "is there a person?"; action detection answers "what
is happening?". This module turns per-person pose keypoints into action
signals — starting with **fall detection**, the most safety-critical action.

Two strategies, in order of reliability:
1. Pose-based: using COCO-17 keypoints, compare the torso orientation
   (shoulders→hips axis). A person standing has a near-vertical torso; a fallen
   person's torso is near-horizontal.
2. Box fallback: when no keypoints are available (plain detection model), use
   the person box aspect ratio — a lying person's box is wider than tall.

These are intentionally simple, explainable heuristics suitable for a first
real action module; they can later be replaced by a temporal action model
without changing callers (the output is just more ``Detection`` objects).
"""

from __future__ import annotations

from app.core.models import BoundingBox, Detection

# COCO-17 keypoint indices.
L_SHOULDER, R_SHOULDER = 5, 6
L_HIP, R_HIP = 11, 12
_MIN_JOINT_CONF = 0.3


def _avg_point(det: Detection, a: int, b: int) -> tuple[float, float] | None:
    kpts = det.keypoints
    if len(kpts) <= max(a, b):
        return None
    xa, ya, ca = kpts[a]
    xb, yb, cb = kpts[b]
    if ca < _MIN_JOINT_CONF or cb < _MIN_JOINT_CONF:
        return None
    return (xa + xb) / 2.0, (ya + yb) / 2.0


def is_fallen(det: Detection) -> bool:
    """Heuristic: is this person detection a fall / person-on-the-ground?"""
    shoulders = _avg_point(det, L_SHOULDER, R_SHOULDER)
    hips = _avg_point(det, L_HIP, R_HIP)
    if shoulders is not None and hips is not None:
        dx = abs(shoulders[0] - hips[0])
        dy = abs(shoulders[1] - hips[1])
        # Torso more horizontal than vertical -> fallen.
        return dx > dy * 1.2

    # Fallback: bounding-box aspect ratio (no usable keypoints).
    box: BoundingBox = det.box
    if box.height <= 0:
        return False
    return (box.width / box.height) > 1.3


def detect_actions(detections: list[Detection]) -> list[Detection]:
    """Return synthetic action detections (e.g. ``fall``) for the frame.

    The originals are left untouched; action results are appended downstream so
    they flow into the event engine (which maps ``fall`` to CRITICAL severity).
    """
    actions: list[Detection] = []
    for det in detections:
        if det.label != "person":
            continue
        if is_fallen(det):
            actions.append(Detection(
                label="fall",
                confidence=det.confidence,
                box=det.box,
                source_plugin=f"{det.source_plugin}:action",
                keypoints=det.keypoints,
            ))
    return actions
