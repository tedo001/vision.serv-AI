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

from app.camera.diagnostics import list_cameras
from app.camera.opencv_source import OpenCVCameraSource
from app.config.settings import AppConfig
from app.core.device import cuda_available, gpu_info, resolve_device
from app.core.logging_config import get_logger
from app.core.models import CameraSourceType
from app.detection.model_catalog import get_model
from app.detection.model_manager import build_detector
from app.detection.null_detector import NullDetector
from app.detection.runner import DetectionRunner
from app.ui.state import AppState, ConnectionStatus
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)

_DEVICE_CHOICES = {"Auto": "auto", "CPU": "cpu", "GPU": "cuda"}
# "Default" -> use the configured camera defaults; others force a resolution.
_RESOLUTIONS: dict[str, tuple[int, int] | None] = {
    "Default": None,
    "640×480": (640, 480),
    "1280×720": (1280, 720),
    "1920×1080": (1920, 1080),
}
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
        index_row = ttk.Frame(controls, style="Surface.TFrame")
        index_row.grid(row=2, column=0, sticky="w")
        self._index_entry = ttk.Entry(index_row, width=6)
        self._index_entry.insert(0, "0")  # 0 = built-in lap cam
        self._index_entry.pack(side="left")
        self._scan_btn = ttk.Button(index_row, text="Scan", width=6, command=self._scan)
        self._scan_btn.pack(side="left", padx=(6, 0))

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

        # Resolution (laptop-camera configuration)
        ttk.Label(controls, text="Resolution", style="SurfaceMuted.TLabel").grid(
            row=1, column=3, sticky="w", padx=(16, 0), pady=(8, 0))
        self._res_cb = ttk.Combobox(controls, values=list(_RESOLUTIONS),
                                    state="readonly", width=12)
        self._res_cb.set("Default")
        self._res_cb.grid(row=2, column=3, sticky="w", padx=(16, 0))

        # Preview-only: test the camera with no model / no weight download.
        self._preview_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Preview only (test camera, no model)",
                        variable=self._preview_only, takefocus=False).grid(
            row=0, column=2, columnspan=3, sticky="w", padx=(16, 0))

        # Camera On/Off toggle
        btns = ttk.Frame(controls, style="Surface.TFrame")
        btns.grid(row=2, column=4, sticky="e", padx=(16, 0))
        self._toggle_btn = ttk.Button(btns, text="▷  Turn Camera On",
                                      style="Accent.TButton", command=self._toggle)
        self._toggle_btn.pack(side="left")
        controls.columnconfigure(4, weight=1)

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
    def _toggle(self) -> None:
        """Single On/Off control for the laptop camera / detection run."""
        if self._runner is not None and self._runner.is_running:
            self._stop()
        else:
            self._start()

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

        if self._preview_only.get():
            detector = NullDetector()  # raw feed: no model, no weight download
            self._stats.configure(text="Preview mode — testing camera (no detection).")
        else:
            detector = build_detector(
                self._config,
                model_override=self.state.active_model.value,
                device_override=device,
            )
        self._runner = DetectionRunner(source, detector, loop_video=loop_video)
        self._runner.start()

        self._toggle_btn.configure(text="■  Turn Camera Off")
        self.state.camera_status.set(ConnectionStatus.ONLINE)
        self.state.status_message.set("Detection running…")
        self._stats.configure(text=f"Starting on {device.upper()} …")
        self._poll()

    def _scan(self) -> None:
        """Find working camera indices off the UI thread, then update the UI."""
        import threading

        self._scan_btn.configure(state="disabled")
        self._stats.configure(text="Scanning for cameras…")

        def worker() -> None:
            try:
                found = list_cameras(max_index=4)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._scan_done(None, str(exc)))
                return
            self.after(0, lambda: self._scan_done(found, None))

        threading.Thread(target=worker, name="camera-scan", daemon=True).start()

    def _scan_done(self, found, error) -> None:
        self._scan_btn.configure(state="normal")
        if error is not None:
            self._stats.configure(text=f"Scan failed: {error}")
            return
        if not found:
            self._stats.configure(text="No cameras found (indices 0–4).")
            return
        first = found[0]
        self._source_kind.set("webcam")
        self._sync_inputs()
        self._index_entry.delete(0, "end")
        self._index_entry.insert(0, str(first.index))
        summary = ", ".join(f"#{p.index} ({p.width}×{p.height})" for p in found)
        self._stats.configure(text=f"Found camera(s): {summary}")

    def _make_source(self) -> tuple[OpenCVCameraSource, bool]:
        cam = self._config.camera
        if self._source_kind.get() == "webcam":
            index = int(self._index_entry.get().strip() or "0")
            res = _RESOLUTIONS.get(self._res_cb.get())
            width, height = res if res is not None else (cam.width, cam.height)
            src = OpenCVCameraSource(index, camera_id=f"webcam{index}",
                                     source_type=CameraSourceType.USB,
                                     buffer_size=cam.buffer_size,
                                     width=width, height=height, fps=cam.target_fps)
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
        self._toggle_btn.configure(text="▷  Turn Camera On")
        self.state.camera_status.set(ConnectionStatus.OFFLINE)
        self.state.fps.set(0.0)
        self.state.status_message.set("Camera off.")

    def on_show(self) -> None:
        gpu, name = gpu_info()
        if gpu:
            self.state.gpu_status.set(ConnectionStatus.ONLINE)
            self.state.gpu_name.set(name)
        else:
            self.state.gpu_status.set(ConnectionStatus.OFFLINE)
