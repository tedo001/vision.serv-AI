"""Declarative catalog of selectable detection models (data only).

Lists the YOLO backbones a user can choose in Settings. Like the profile
catalog, this is pure, framework-agnostic data: the Settings UI renders it,
and the detection layer (``ModelManager`` / ``YoloDetector``) consumes the
``weights`` filename to instantiate the model. Adding a model is a one-entry
change here — no UI or engine edits.

Weight files auto-download from Ultralytics on first use, so only the
filename is stored, not the binary. Sizes are approximate (detection task).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelInfo:
    key: str
    display_name: str
    weights: str          # Ultralytics weight filename (auto-downloaded)
    family: str           # "YOLO11" | "YOLO26"
    size_label: str       # "Nano" | "X-Large"
    profile: str          # "fast" | "balanced" | "accurate"
    approx_size_mb: int
    description: str
    task: str = "detect"  # "detect" (objects) | "pose" (skeleton keypoints)


# Ordered fast -> accurate. Keys are stable identifiers stored in config.
MODELS: dict[str, ModelInfo] = {
    "yolo11n": ModelInfo(
        key="yolo11n",
        display_name="YOLO11 Nano",
        weights="yolo11n.pt",
        family="YOLO11",
        size_label="Nano",
        profile="fast",
        approx_size_mb=6,
        description="Lightweight, real-time on CPU/edge. Lowest accuracy ceiling.",
    ),
    "yolo26n": ModelInfo(
        key="yolo26n",
        display_name="YOLO26 Nano",
        weights="yolo26n.pt",
        family="YOLO26",
        size_label="Nano",
        profile="fast",
        approx_size_mb=5,
        description="Newest nano backbone; NMS-free, fast and edge-friendly.",
    ),
    "yolo26x": ModelInfo(
        key="yolo26x",
        display_name="YOLO26 X-Large",
        weights="yolo26x.pt",
        family="YOLO26",
        size_label="X-Large",
        profile="accurate",
        approx_size_mb=113,
        description="Highest accuracy; best for industrial detail. Needs a GPU "
                    "for real-time. Large download on first use.",
    ),
    # --- Pose / skeleton models (enable action detection, e.g. falls) -------
    "yolo11n-pose": ModelInfo(
        key="yolo11n-pose",
        display_name="YOLO11 Nano — Pose",
        weights="yolo11n-pose.pt",
        family="YOLO11",
        size_label="Nano",
        profile="fast",
        approx_size_mb=6,
        description="Skeleton keypoints for people; powers fall/action "
                    "detection. Fast, runs on CPU.",
        task="pose",
    ),
    "yolo11x-pose": ModelInfo(
        key="yolo11x-pose",
        display_name="YOLO11 X-Large — Pose",
        weights="yolo11x-pose.pt",
        family="YOLO11",
        size_label="X-Large",
        profile="accurate",
        approx_size_mb=113,
        description="High-accuracy skeleton keypoints for action detection. "
                    "GPU recommended.",
        task="pose",
    ),
}

DEFAULT_MODEL_KEY = "yolo26n"


def get_model(key: str) -> ModelInfo | None:
    """Return the model info for ``key`` (case-insensitive), or None."""
    return MODELS.get(key.lower())


def is_known_model(key: str) -> bool:
    return key.lower() in MODELS
