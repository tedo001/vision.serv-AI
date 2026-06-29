"""Ultralytics YOLO detector implementing the core ``DetectorPlugin`` port.

This is the real, reusable detection component used for industrial object
detection. It wraps an Ultralytics YOLO model (YOLO11 / YOLO26 family) behind
the platform's interface so the rest of the system never imports ultralytics
directly — the backbone can be swapped or upgraded in one place.

The ultralytics import is deferred to :meth:`load` so the package, tests, and
headless tooling do not require the (heavy) dependency unless a model is
actually enabled. Weights auto-download from Ultralytics on first use.

Live wiring (camera -> detector -> tracker -> events) lands in Phases 7-8;
this component is complete and unit-testable on its own today.
"""

from __future__ import annotations

from app.core.exceptions import DetectionError
from app.core.interfaces import Frame
from app.core.logging_config import get_logger
from app.core.models import BoundingBox, Detection
from app.detection.model_catalog import ModelInfo, get_model

logger = get_logger(__name__)


class YoloDetector:
    """A detector backed by a single Ultralytics YOLO model."""

    def __init__(
        self,
        model_key: str,
        *,
        confidence: float = 0.45,
        iou: float = 0.50,
        device: str = "auto",
        model_dir: str = "assets/models",
    ) -> None:
        info = get_model(model_key)
        if info is None:
            raise DetectionError(f"Unknown model key: {model_key!r}")
        self._info: ModelInfo = info
        self._confidence = confidence
        self._iou = iou
        self._device = None if device == "auto" else device
        self._model_dir = model_dir
        self._model = None  # lazily loaded ultralytics model

    @property
    def name(self) -> str:
        return self._info.key

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load the model weights. Raises ``DetectionError`` on failure."""
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO  # deferred heavy import
        except ImportError as exc:
            raise DetectionError(
                "ultralytics is not installed. Run 'pip install ultralytics' "
                "to enable model-based detection."
            ) from exc

        weights_path = f"{self._model_dir}/{self._info.weights}"
        try:
            # Ultralytics resolves a bare filename by auto-downloading; a path
            # is used if the weights already exist locally.
            self._model = YOLO(weights_path)
        except Exception:
            logger.info("Weights not found at %s; letting ultralytics resolve %s",
                        weights_path, self._info.weights)
            try:
                self._model = YOLO(self._info.weights)
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                raise DetectionError(
                    f"Failed to load model {self._info.display_name} "
                    f"({self._info.weights}): {exc}"
                ) from exc
        logger.info("Loaded detection model: %s", self._info.display_name)

    def detect(self, frame: Frame) -> list[Detection]:
        """Run inference on one frame and map results to ``Detection``s."""
        if self._model is None:
            raise DetectionError("detect() called before load().")
        try:
            results = self._model.predict(
                frame.image,
                conf=self._confidence,
                iou=self._iou,
                device=self._device,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise DetectionError(f"Inference failed: {exc}") from exc

        return self._map_results(results)

    def unload(self) -> None:
        self._model = None
        logger.debug("Unloaded model %s", self._info.key)

    # -- internal ------------------------------------------------------------
    def _map_results(self, results) -> list[Detection]:
        detections: list[Detection] = []
        for result in results:
            names = getattr(result, "names", {}) or {}
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            keypoints = self._extract_keypoints(result)
            for i, box in enumerate(boxes):
                xyxy = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                detections.append(
                    Detection(
                        label=str(names.get(class_id, class_id)),
                        confidence=float(box.conf[0]),
                        box=BoundingBox(*xyxy),
                        source_plugin=self._info.key,
                        class_id=class_id,
                        keypoints=keypoints[i] if i < len(keypoints) else (),
                    )
                )
        return detections

    @staticmethod
    def _extract_keypoints(result) -> list[tuple[tuple[float, float, float], ...]]:
        """Pull per-detection (x, y, conf) joints from a pose result, if any."""
        kp = getattr(result, "keypoints", None)
        if kp is None or getattr(kp, "data", None) is None:
            return []
        out: list[tuple[tuple[float, float, float], ...]] = []
        for person in kp.data:  # shape (num_joints, 3)
            joints = tuple((float(x), float(y), float(c)) for x, y, c in person.tolist())
            out.append(joints)
        return out
