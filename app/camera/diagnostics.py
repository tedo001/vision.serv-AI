"""Camera diagnostics: detect and verify available cameras.

A small testing/troubleshooting module focused on the common case of a laptop
camera. ``probe_camera`` opens an index, grabs a frame, and reports resolution
and success; ``list_cameras`` scans a range of indices for working devices.

``cv2`` is imported lazily so this module imports without OpenCV; calling a
probe without OpenCV installed raises a clear ``CameraError``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import CameraError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CameraProbe:
    """Result of probing a single camera index."""

    index: int
    available: bool
    width: int = 0
    height: int = 0
    message: str = ""


def _load_cv2():
    try:
        import cv2
        return cv2
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise CameraError(
            "opencv-python is not installed. Run 'pip install opencv-python' "
            "to test cameras."
        ) from exc


def probe_camera(index: int, *, warmup_reads: int = 2) -> CameraProbe:
    """Open camera ``index``, read a frame, and report the outcome.

    A couple of warm-up reads are performed because some webcams (notably
    laptop cameras) return an empty first frame while the sensor initializes.
    """
    cv2 = _load_cv2()
    cap = cv2.VideoCapture(index)
    try:
        if not cap.isOpened():
            return CameraProbe(index, False, message="could not open device")
        frame = None
        for _ in range(max(1, warmup_reads)):
            ok, frame = cap.read()
            if ok and frame is not None:
                break
        if frame is None:
            return CameraProbe(index, False, message="opened but no frame")
        h, w = frame.shape[:2]
        return CameraProbe(index, True, width=int(w), height=int(h), message="ok")
    finally:
        cap.release()


def list_cameras(max_index: int = 5) -> list[CameraProbe]:
    """Probe indices ``0..max_index`` and return those that work.

    Note: opening real devices is relatively slow; keep ``max_index`` small.
    """
    found: list[CameraProbe] = []
    for index in range(max_index + 1):
        probe = probe_camera(index)
        if probe.available:
            logger.info("Camera %d available: %dx%d", index, probe.width, probe.height)
            found.append(probe)
    return found
