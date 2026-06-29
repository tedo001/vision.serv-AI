"""Video Detection tab: run the selected model on a lap cam or a video file.

This is the visible vertical slice — pick a source (built-in webcam / laptop
camera, or a video file), pick a compute device (Auto / CPU / GPU), press
Start, and watch live bounding boxes from the model chosen in Settings.

Architecture: the view owns no detection logic. It builds a ``CameraSource``
and a ``YoloDetector``, hands them to a background ``DetectionRunner``, and
polls the runner's latest annotated frame on the Tk event loop (via
``after``), converting it to a Tk image for display. All GUI updates happen on
the main thread; all capture/inference happens on the runner thread.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from app.camera.opencv_source import OpenCVCameraSource
from app.config.settings import AppConfig
from app.core.device import cuda_available, gpu_info, resolve_device
from app.core.logging_config import get_logger
from app.core.models import CameraSourceType
from app.detection.model_catalog import get_model
from app.detection.model_manager import build_detector
from app.detection.runner import DetectionRunner
from app.ui.state import AppState, ConnectionStatus
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)

_DEVICE_CHOICES = {"Auto": "auto", "CPU": "cpu", "GPU": "cuda"}
_POLL_MS = 30


class VideoDetectionView(BaseView):
    def __init__(self, parent: tk.Widget, state: AppState, config: AppConfig) -> None:
        self._config = config
        self._runner: DetectionRunner | None = None
        self._poll_job: str | None = None
        self._photo = None  # keep a ref so Tk doesn't GC the image
        super().__init__(parent, state)

    # -- layout --------------------------------------------------------------
    def build(self) -> None:
        section_title(self, "Video Detection",
                      "Run the active model on a laptop camera or a video file").pack(
            anchor="w", fill="x")

        controls = ttk.Frame(self, style="Surface.TFrame", padding=14)
        controls.pack(fill="x", pady=(12, 12))

        # Source selection
        self._source_kind = tk.StringVar(value="webcam")
        ttk.Radiobutton(controls, text="Laptop / USB camera", value="webcam",
                        variable=self._source_kind, takefocus=False,
                        command=self._sync_inputs).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(controls, text="Video file", value="file",
                        variable=self._source_kind, takefocus=False,
                        command=self._sync_inputs).grid(row=0, column=1, sticky="w", padx=(16, 0))

        ttk.Label(controls, text="Camera index", style="SurfaceMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        self._index_entry = ttk.Entry(controls, width=8)
        self._index_entry.insert(0, "0")  # 0 = built-in lap cam
        self._index_entry.grid(row=2, column=0, sticky="w")

        ttk.Label(controls, text="Video file", style="SurfaceMuted.TLabel").grid(
            row=1, column=1, sticky="w", pady=(8, 0))
        file_row = ttk.Frame(controls, style="Surface.TFrame")
        file_row.grid(row=2, column=1, sticky="w")
        self._file_entry = ttk.Entry(file_row, width=34)
        self._file_entry.pack(side="left")
        self._browse_btn = ttk.Button(file_row, text="Browse", command=self._browse)
        self._browse_btn.pack(side="left", padx=(6, 0))

        # Device
        ttk.Label(controls, text="Device", style="SurfaceMuted.TLabel").grid(
            row=1, column=2, sticky="w", padx=(16, 0), pady=(8, 0))
        self._device_cb = ttk.Combobox(controls, values=list(_DEVICE_CHOICES),
                                       state="readonly", width=8)
        self._device_cb.set("Auto")
        self._device_cb.grid(row=2, column=2, sticky="w", padx=(16, 0))

        # Start / Stop
        btns = ttk.Frame(controls, style="Surface.TFrame")
        btns.grid(row=2, column=3, sticky="e", padx=(16, 0))
        self._start_btn = ttk.Button(btns, text="▷ Start", style="Accent.TButton",
                                     command=self._start)
        self._start_btn.pack(side="left")
        self._stop_btn = ttk.Button(btns, text="■ Stop", command=self._stop,
                                    state="disabled")
        self._stop_btn.pack(side="left", padx=(6, 0))
        controls.columnconfigure(3, weight=1)

        # Active-model hint
        self._model_hint = ttk.Label(self, style="Muted.TLabel")
        self._model_hint.pack(anchor="w")
        self.state.active_model.subscribe(self._update_model_hint)

        # Video display
        display_wrap = ttk.Frame(self, style="Surface.TFrame", padding=2)
        display_wrap.pack(fill="both", expand=True, pady=(8, 8))
        self._display = ttk.Label(
            display_wrap, anchor="center", justify="center",
            style="SurfaceMuted.TLabel",
            text="▷  Press Start to begin detection.",
        )
        self._display.pack(fill="both", expand=True)

        # Stats strip
        self._stats = ttk.Label(self, style="Muted.TLabel", text="Idle.")
        self._stats.pack(anchor="w")

        self._sync_inputs()

    # -- input helpers -------------------------------------------------------
    def _sync_inputs(self) -> None:
        webcam = self._source_kind.get() == "webcam"
        self._index_entry.configure(state="normal" if webcam else "disabled")
        self._file_entry.configure(state="disabled" if webcam else "normal")
        self._browse_btn.configure(state="disabled" if webcam else "normal")

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")],
        )
        if path:
            self._file_entry.delete(0, "end")
            self._file_entry.insert(0, path)

    def _update_model_hint(self, model_key: str) -> None:
        info = get_model(model_key)
        name = info.display_name if info else model_key
        self._model_hint.configure(
            text=f"Active model: {name}  (change in Settings → AI Detection Model)")

    # -- run control ---------------------------------------------------------
    def _start(self) -> None:
        if self._runner and self._runner.is_running:
            return
        try:
            source, loop_video = self._make_source()
        except (ValueError, Exception) as exc:  # noqa: BLE001
            self._stats.configure(text=f"Cannot start: {exc}")
            return

        device = _DEVICE_CHOICES[self._device_cb.get()]
        if device == "cuda" and not cuda_available():
            device = "cpu"
            self.state.status_message.set("GPU not available — using CPU.")

        detector = build_detector(
            self._config,
            model_override=self.state.active_model.value,
            device_override=device,
        )
        self._runner = DetectionRunner(source, detector, loop_video=loop_video)
        self._runner.start()

        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self.state.camera_status.set(ConnectionStatus.ONLINE)
        self.state.status_message.set("Detection running…")
        self._stats.configure(text=f"Starting on {device.upper()} …")
        self._poll()

    def _make_source(self) -> tuple[OpenCVCameraSource, bool]:
        if self._source_kind.get() == "webcam":
            index = int(self._index_entry.get().strip() or "0")
            src = OpenCVCameraSource(index, camera_id=f"webcam{index}",
                                     source_type=CameraSourceType.USB,
                                     buffer_size=self._config.camera.buffer_size)
            return src, False
        path = self._file_entry.get().strip()
        if not path:
            raise ValueError("choose a video file first")
        src = OpenCVCameraSource(path, camera_id="videofile",
                                 source_type=CameraSourceType.FILE)
        return src, True  # loop files for continuous demo

    def _poll(self) -> None:
        runner = self._runner
        if runner is None:
            return
        if runner.error:
            self._stats.configure(text=f"Error: {runner.error}")
            self._stop()
            return

        result = runner.latest()
        if result is not None:
            self._render(result.image)
            self.state.fps.set(result.fps)
            self._stats.configure(
                text=f"FPS {result.fps:5.1f}   •   {len(result.detections)} objects"
                     f"   •   frame {result.frame_index}")

        if not runner.is_running and result is None:
            # source ended before producing frames
            self._stats.configure(text="Source produced no frames.")
            self._stop()
            return

        self._poll_job = self.after(_POLL_MS, self._poll)

    def _render(self, bgr_image) -> None:
        import cv2
        from PIL import Image, ImageTk

        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        # Fit within the display area while preserving aspect ratio.
        w = max(self._display.winfo_width(), 320)
        h = max(self._display.winfo_height(), 240)
        img.thumbnail((w, h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._display.configure(image=self._photo, text="")

    def _stop(self) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        if self._runner is not None:
            self._runner.stop()
            self._runner = None
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self.state.camera_status.set(ConnectionStatus.OFFLINE)
        self.state.fps.set(0.0)
        self.state.status_message.set("Detection stopped.")

    def on_show(self) -> None:
        gpu, name = gpu_info()
        if gpu:
            self.state.gpu_status.set(ConnectionStatus.ONLINE)
            self.state.gpu_name.set(name)
        else:
            self.state.gpu_status.set(ConnectionStatus.OFFLINE)
