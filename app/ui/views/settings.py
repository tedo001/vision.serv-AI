"""Settings: AI model selection + the resolved application configuration.

The top card is interactive: choose a YOLO backbone (YOLO11 / YOLO26), toggle
whether it runs, and tune the confidence/IoU thresholds. Applying updates the
live ``AppState`` (so the detection engine picks it up) and persists to
``config/default.yaml`` via the injected callback. The lower section shows the
full resolved config for transparency.

The view stays thin: it gathers widget values and hands them to ``on_apply``;
it does not perform config IO or build models itself.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from app.config.settings import AppConfig
from app.core.logging_config import get_logger
from app.detection.model_catalog import MODELS, get_model
from app.ui.state import AppState
from app.ui.theme import PALETTE
from app.ui.views.base import BaseView
from app.ui.widgets import section_title

logger = get_logger(__name__)

# (active_model, enabled, confidence, iou, device)
ApplyModelsCallback = Callable[[str, bool, float, float, str], None]

_DEVICE_CHOICES = {"Auto": "auto", "CPU": "cpu", "GPU": "cuda"}
_DEVICE_LABELS = {v: k for k, v in _DEVICE_CHOICES.items()}


class SettingsView(BaseView):
    def __init__(
        self,
        parent: tk.Widget,
        state: AppState,
        config: AppConfig,
        on_apply: Optional[ApplyModelsCallback] = None,
    ) -> None:
        self._config = config
        self._on_apply = on_apply
        super().__init__(parent, state)

    def build(self) -> None:
        section_title(self, "Settings",
                      "Select a detection model and tune thresholds").pack(
            anchor="w", fill="x")

        self._build_model_card()
        self._build_config_display()

    # -- AI model selection --------------------------------------------------
    def _build_model_card(self) -> None:
        card = ttk.Frame(self, style="Surface.TFrame", padding=16)
        card.pack(fill="x", pady=16)

        ttk.Label(card, text="AI Detection Model", style="H2.TLabel",
                  background=PALETTE.surface).pack(anchor="w")
        ttk.Label(card, text="When enabled, the selected model runs on every "
                             "camera for industrial object detection.",
                  style="SurfaceMuted.TLabel").pack(anchor="w", pady=(2, 12))

        # Model selector (display names -> keys)
        self._key_by_label = {m.display_name: m.key for m in MODELS.values()}
        labels = list(self._key_by_label.keys())
        current_label = next(
            (m.display_name for m in MODELS.values()
             if m.key == self.state.active_model.value),
            labels[0],
        )

        row1 = ttk.Frame(card, style="Surface.TFrame")
        row1.pack(fill="x")
        ttk.Label(row1, text="Model", style="SurfaceMuted.TLabel").pack(side="left")
        self._model_cb = ttk.Combobox(row1, values=labels, state="readonly", width=22)
        self._model_cb.set(current_label)
        self._model_cb.pack(side="left", padx=(8, 16))
        self._model_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_info())

        self._enabled_var = tk.BooleanVar(value=self.state.model_enabled.value)
        ttk.Checkbutton(row1, text="Enable for detection",
                        variable=self._enabled_var, takefocus=False).pack(side="left")

        ttk.Label(row1, text="Device", style="SurfaceMuted.TLabel").pack(
            side="left", padx=(16, 4))
        self._device_cb = ttk.Combobox(row1, values=list(_DEVICE_CHOICES),
                                       state="readonly", width=7)
        self._device_cb.set(_DEVICE_LABELS.get(self._config.detection.device, "Auto"))
        self._device_cb.pack(side="left")

        # Threshold sliders
        self._conf_var = tk.DoubleVar(value=self.state.confidence.value)
        self._iou_var = tk.DoubleVar(value=self.state.iou.value)
        self._conf_lbl = self._slider(card, "Confidence threshold", self._conf_var)
        self._iou_lbl = self._slider(card, "IoU (NMS) threshold", self._iou_var)

        # Model info + apply
        self._info_lbl = ttk.Label(card, text="", style="SurfaceMuted.TLabel",
                                   wraplength=720, justify="left")
        self._info_lbl.pack(anchor="w", pady=(4, 12))

        ttk.Button(card, text="Apply & Save", style="Accent.TButton",
                   command=self._apply).pack(anchor="w")

        self._refresh_info()

    def _slider(self, parent: ttk.Frame, label: str, var: tk.DoubleVar) -> ttk.Label:
        row = ttk.Frame(parent, style="Surface.TFrame")
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=label, style="SurfaceMuted.TLabel", width=22).pack(side="left")
        value_lbl = ttk.Label(row, text=f"{var.get():.2f}", background=PALETTE.surface,
                              foreground=PALETTE.text, font=("Segoe UI Semibold", 9), width=5)
        value_lbl.pack(side="right")
        scale = ttk.Scale(row, from_=0.0, to=1.0, variable=var, orient="horizontal",
                          command=lambda _v: value_lbl.configure(text=f"{var.get():.2f}"))
        scale.pack(side="left", fill="x", expand=True, padx=8)
        return value_lbl

    def _refresh_info(self) -> None:
        info = get_model(self._key_by_label[self._model_cb.get()])
        if info is None:
            self._info_lbl.configure(text="")
            return
        self._info_lbl.configure(
            text=f"{info.family} · {info.size_label} · ~{info.approx_size_mb} MB "
                 f"({info.profile}).  {info.description}"
        )

    def _apply(self) -> None:
        model_key = self._key_by_label[self._model_cb.get()]
        enabled = bool(self._enabled_var.get())
        conf = round(float(self._conf_var.get()), 2)
        iou = round(float(self._iou_var.get()), 2)
        device = _DEVICE_CHOICES[self._device_cb.get()]
        logger.info("Apply model settings: model=%s enabled=%s conf=%.2f iou=%.2f dev=%s",
                    model_key, enabled, conf, iou, device)

        if self._on_apply is not None:
            self._on_apply(model_key, enabled, conf, iou, device)
        else:  # standalone fallback: update live state only
            self.state.active_model.set(model_key)
            self.state.model_enabled.set(enabled)
            self.state.confidence.set(conf)
            self.state.iou.set(iou)

        info = get_model(model_key)
        name = info.display_name if info else model_key
        status = f"Detection model set to {name}" + (" (enabled)" if enabled else " (disabled)")
        self.state.status_message.set(status)

    # -- read-only config display -------------------------------------------
    def _build_config_display(self) -> None:
        c = self._config
        groups = {
            "General": [
                ("Product name", c.product_name),
                ("Active profile", c.active_profile),
                ("Database path", c.database_path),
            ],
            "Detection": [
                ("Active model", c.detection.active_model),
                ("Enabled", c.detection.enabled),
                ("Device", c.detection.device),
                ("Model dir", c.detection.model_dir),
            ],
            "Camera defaults": [
                ("Reconnect (s)", c.camera.reconnect_seconds),
                ("Target FPS", c.camera.target_fps),
                ("Buffer size", c.camera.buffer_size),
            ],
            "Alerts / Logging": [
                ("Sound enabled", c.alert.enable_sound),
                ("Min severity", c.alert.min_severity),
                ("Log level", c.logging.level),
                ("Theme", c.ui.theme),
            ],
        }

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        for i in range(2):
            container.columnconfigure(i, weight=1, uniform="settings")

        for idx, (title, rows) in enumerate(groups.items()):
            card = ttk.Frame(container, style="Surface.TFrame", padding=16)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=8, pady=8)
            ttk.Label(card, text=title, style="H2.TLabel",
                      background=PALETTE.surface).pack(anchor="w", pady=(0, 8))
            for label, value in rows:
                row = ttk.Frame(card, style="Surface.TFrame")
                row.pack(fill="x", pady=2)
                ttk.Label(row, text=label, background=PALETTE.surface,
                          foreground=PALETTE.text_muted, font=("Segoe UI", 9)).pack(side="left")
                ttk.Label(row, text=str(value), background=PALETTE.surface,
                          foreground=PALETTE.text, font=("Segoe UI Semibold", 9)).pack(side="right")
