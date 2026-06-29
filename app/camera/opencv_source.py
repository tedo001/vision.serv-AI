"""OpenCV-backed camera source (Phase 7, minimal vertical slice).

One adapter covers all four source kinds because OpenCV's ``VideoCapture``
opens a webcam index, a file path, or an RTSP/HTTP URL through the same API:

- USB / laptop camera  -> integer device index (0 is the built-in lap cam)
- File                 -> path string
- RTSP / IP            -> url string

``cv2`` is imported lazily inside :meth:`open` so importing this module (and
running tests) does not require OpenCV to be installed.
"""

from __future__ import annotations

import sys
import time
from typing import Optional

from app.camera.frame import FrameData
from app.core.exceptions import CameraError
from app.core.logging_config import get_logger
from app.core.models import CameraSourceType

logger = get_logger(__name__)


class OpenCVCameraSource:
    """A :class:`app.core.interfaces.CameraSource` backed by OpenCV.

    For laptop/USB cameras a platform-appropriate capture backend is selected
    (DirectShow on Windows, AVFoundation on macOS, V4L2 on Linux). This is the
    single most important factor in webcams opening quickly and reliably —
    Windows' default MSMF backend, in particular, is slow and flaky for many
    built-in laptop cameras. Requested resolution/FPS are applied after open.
    """

    def __init__(
        self,
        spec: str | int,
        *,
        camera_id: str = "cam0",
        source_type: CameraSourceType = CameraSourceType.USB,
        buffer_size: int = 1,
        width: int = 0,
        height: int = 0,
        fps: int = 0,
    ) -> None:
        self._spec = spec
        self._camera_id = camera_id
        self._source_type = source_type
        self._buffer_size = buffer_size
        self._width = width
        self._height = height
        self._fps = fps
        self._cap = None
        self._frame_index = 0

    @property
    def camera_id(self) -> str:
        return self._camera_id

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @staticmethod
    def resolve_target(source_type: CameraSourceType, spec: str | int) -> str | int:
        """Map a (type, spec) pair to the value OpenCV expects.

        Webcam indices become ints; files and network streams stay strings.
        """
        if source_type is CameraSourceType.USB:
            return int(spec)
        return str(spec)

    @staticmethod
    def preferred_backend(cv2, source_type: CameraSourceType, platform: str = sys.platform):
        """Pick a capture backend. Only webcams benefit from a platform backend.

        Returns the cv2 backend constant, or ``cv2.CAP_ANY`` to let OpenCV
        choose (used for files and network streams).
        """
        if source_type is not CameraSourceType.USB:
            return cv2.CAP_ANY
        if platform.startswith("win"):
            return getattr(cv2, "CAP_DSHOW", cv2.CAP_ANY)
        if platform == "darwin":
            return getattr(cv2, "CAP_AVFOUNDATION", cv2.CAP_ANY)
        return getattr(cv2, "CAP_V4L2", cv2.CAP_ANY)

    def open(self) -> None:
        try:
            import cv2  # deferred heavy import
        except ImportError as exc:
            raise CameraError(
                "opencv-python is not installed. Run 'pip install "
                "opencv-python' to use camera/video capture."
            ) from exc

        target = self.resolve_target(self._source_type, self._spec)
        backend = self.preferred_backend(cv2, self._source_type)
        self._cap = cv2.VideoCapture(target, backend)
        if not self._cap.isOpened():
            self._cap = None
            raise CameraError(
                f"Could not open source {target!r} ({self._source_type.value}). "
                f"For a laptop camera, try a different index (use Scan)."
            )

        self._configure(cv2)
        self._frame_index = 0
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("Opened %s source %r as %s at %dx%d",
                    self._source_type.value, target, self._camera_id,
                    actual_w, actual_h)

    def _configure(self, cv2) -> None:
        """Apply buffer/resolution/FPS. Unsupported props fail silently."""
        def _safe_set(prop: int, value: float) -> None:
            try:
                self._cap.set(prop, value)
            except Exception:  # backend may not support the property
                pass

        _safe_set(cv2.CAP_PROP_BUFFERSIZE, self._buffer_size)
        if self._width > 0:
            _safe_set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        if self._height > 0:
            _safe_set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        if self._fps > 0:
            _safe_set(cv2.CAP_PROP_FPS, self._fps)

    def read(self) -> Optional[FrameData]:
        if self._cap is None:
            raise CameraError("read() called before open().")
        ok, image = self._cap.read()
        if not ok or image is None:
            return None  # end of file or transient failure
        self._frame_index += 1
        return FrameData(
            image=image,
            camera_id=self._camera_id,
            frame_index=self._frame_index,
            timestamp=time.time(),
        )

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.debug("Released source %s", self._camera_id)
