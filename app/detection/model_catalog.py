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
    task: str = "detect"   # "detect" | "pose" | "segment"
    loader: str = "yolo"   # "yolo" | "rtdetr" | "sam" (which Ultralytics class)


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
    "yolo26s": ModelInfo(
        key="yolo26s",
        display_name="YOLO26 Small",
        weights="yolo26s.pt",
        family="YOLO26",
        size_label="Small",
        profile="balanced",
        approx_size_mb=20,
        description="Balanced speed/accuracy for general detection.",
    ),
    "yolo11m": ModelInfo(
        key="yolo11m",
        display_name="YOLO11 Medium",
        weights="yolo11m.pt",
        family="YOLO11",
        size_label="Medium",
        profile="balanced",
        approx_size_mb=40,
        description="Mid-size detector; good accuracy without a large GPU.",
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
    "yolo26n-pose": ModelInfo(
        key="yolo26n-pose",
        display_name="YOLO26 Nano — Pose",
        weights="yolo26n-pose.pt",
        family="YOLO26",
        size_label="Nano",
        profile="fast",
        approx_size_mb=6,
        description="Newest nano skeleton model; NMS-free, edge-friendly.",
        task="pose",
    ),
    # --- Segmentation (tighter masks -> better detection rate) --------------
    "yolo11n-seg": ModelInfo(
        key="yolo11n-seg",
        display_name="YOLO11 Nano — Segment",
        weights="yolo11n-seg.pt",
        family="YOLO11",
        size_label="Nano",
        profile="fast",
        approx_size_mb=7,
        description="Instance segmentation masks (not just boxes). Fast.",
        task="segment",
    ),
    "yolo26n-seg": ModelInfo(
        key="yolo26n-seg",
        display_name="YOLO26 Nano — Segment",
        weights="yolo26n-seg.pt",
        family="YOLO26",
        size_label="Nano",
        profile="fast",
        approx_size_mb=7,
        description="Newest nano segmentation model.",
        task="segment",
    ),
    # --- RT-DETR (transformer detector; strong accuracy) --------------------
    "rtdetr-l": ModelInfo(
        key="rtdetr-l",
        display_name="RT-DETR Large",
        weights="rtdetr-l.pt",
        family="RT-DETR",
        size_label="Large",
        profile="accurate",
        approx_size_mb=63,
        description="Transformer-based detector; high accuracy, GPU recommended.",
        task="detect",
        loader="rtdetr",
    ),
    # --- SAM2 (promptable segmentation; experimental) -----------------------
    "sam2-b": ModelInfo(
        key="sam2-b",
        display_name="SAM2 Base (experimental)",
        weights="sam2_b.pt",
        family="SAM2",
        size_label="Base",
        profile="accurate",
        approx_size_mb=162,
        description="Segment Anything 2. Heavy; promptable segmentation. "
                    "Experimental in this build.",
        task="segment",
        loader="sam",
    ),
}

DEFAULT_MODEL_KEY = "yolo26n"


def get_model(key: str) -> ModelInfo | None:
    """Return the model info for ``key`` (case-insensitive), or None."""
    return MODELS.get(key.lower()) or MODELS.get(key)


def is_known_model(key: str) -> bool:
    return key.lower() in MODELS or key in MODELS


def register_model(info: ModelInfo) -> None:
    """Add (or replace) a model in the catalog at runtime.

    Used to surface custom-trained weights discovered in the model directory
    so they are selectable exactly like the built-in models.
    """
    MODELS[info.key] = info
