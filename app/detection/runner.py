"""Detection runner: the capture -> detect -> annotate loop (mini Phase 8).

Pulls frames from a ``CameraSource``, runs a ``DetectorPlugin`` on each, and
stores the latest annotated frame + detections + smoothed FPS for a consumer
(the UI) to poll. Framework-agnostic and thread-safe; it knows nothing about
Tkinter.

Threading model: the loop runs on a daemon thread. The UI polls
:meth:`latest` on its own clock and renders — the runner never touches GUI
state, which keeps Tkinter's single-threaded contract intact.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from app.core.interfaces import CameraSource, DetectorPlugin
from app.core.logging_config import get_logger
from app.core.models import Detection
from app.detection.drawing import draw_detections

logger = get_logger(__name__)

Annotator = Callable[[np.ndarray, list[Detection]], np.ndarray]


@dataclass(slots=True)
class RunnerResult:
    """Snapshot of the most recently processed frame."""

    image: np.ndarray            # annotated BGR frame
    detections: list[Detection]
    fps: float
    frame_index: int


class DetectionRunner:
    """Runs a detector over a source on a background thread."""

    def __init__(
        self,
        source: CameraSource,
        detector: DetectorPlugin,
        *,
        loop_video: bool = False,
        annotator: Annotator = draw_detections,
        class_filter: frozenset[str] | None = None,
    ) -> None:
        self._source = source
        self._detector = detector
        self._loop_video = loop_video
        self._annotate = annotator
        # When set, only detections whose label is in the set are kept. This
        # is how an industry profile focuses detection on relevant objects.
        self._class_filter = class_filter
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest: Optional[RunnerResult] = None
        self._error: Optional[str] = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, name="detection-runner",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def error(self) -> Optional[str]:
        return self._error

    def latest(self) -> Optional[RunnerResult]:
        with self._lock:
            return self._latest

    # -- loop ----------------------------------------------------------------
    def _run(self) -> None:
        """Capture/detect loop. Returns when stopped or the source ends.

        Callable directly (synchronously) for deterministic testing, or via
        :meth:`start` on a background thread for live use.
        """
        try:
            self._detector.load()
            self._source.open()
        except Exception as exc:  # noqa: BLE001 - surface to UI, don't crash
            self._error = str(exc)
            logger.error("Runner failed to start: %s", exc)
            return

        fps = 0.0
        last = time.time()
        try:
            while not self._stop.is_set():
                frame = self._source.read()
                if frame is None:  # end of file / stream gap
                    if self._loop_video:
                        self._source.release()
                        self._source.open()
                        continue
                    break

                detections = self._detector.detect(frame)
                if self._class_filter is not None:
                    detections = [d for d in detections
                                  if d.label in self._class_filter]
                annotated = self._annotate(frame.image, detections)

                now = time.time()
                dt = now - last
                last = now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)

                with self._lock:
                    self._latest = RunnerResult(
                        image=annotated, detections=detections,
                        fps=fps, frame_index=frame.frame_index,
                    )
        finally:
            self._source.release()
            logger.debug("Runner loop ended")
