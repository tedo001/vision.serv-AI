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

import time
from typing import Optional

from app.camera.frame import FrameData
from app.core.exceptions import CameraError
from app.core.logging_config import get_logger
from app.core.models import CameraSourceType

logger = get_logger(__name__)


class OpenCVCameraSource:
    """A :class:`app.core.interfaces.CameraSource` backed by OpenCV."""

    def __init__(
        self,
        spec: str | int,
        *,
        camera_id: str = "cam0",
        source_type: CameraSourceType = CameraSourceType.USB,
        buffer_size: int = 1,
    ) -> None:
        self._spec = spec
        self._camera_id = camera_id
        self._source_type = source_type
        self._buffer_size = buffer_size
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

    def open(self) -> None:
        try:
            import cv2  # deferred heavy import
        except ImportError as exc:
            raise CameraError(
                "opencv-python is not installed. Run 'pip install "
                "opencv-python' to use camera/video capture."
            ) from exc

        target = self.resolve_target(self._source_type, self._spec)
        self._cap = cv2.VideoCapture(target)
        if not self._cap.isOpened():
            self._cap = None
            raise CameraError(
                f"Could not open source {target!r} ({self._source_type.value})."
            )
        try:
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, self._buffer_size)
        except Exception:  # property unsupported on some backends; non-fatal
            pass
        self._frame_index = 0
        logger.info("Opened %s source %r as %s",
                    self._source_type.value, target, self._camera_id)

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
