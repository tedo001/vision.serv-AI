"""Train / fine-tune a custom YOLO model on your own labeled dataset.

This is the bridge from "generic detection" to "detects YOUR incidents". You
provide a labeled dataset (YOLO format, described in datasets/README.md); this
fine-tunes a YOLO backbone on it and copies the best weights into the model
directory so the app can select and run them.

Run on a machine with a GPU for real datasets; CPU works for tiny smoke tests.

Examples
--------
# Smoke test the whole pipeline on Ultralytics' tiny bundled dataset:
    python -m tools.train --data coco8.yaml --base yolo11n.pt --epochs 2

# Train a real safety model on your dataset:
    python -m tools.train --data datasets/safety/data.yaml \
        --base yolo11n.pt --epochs 100 --imgsz 640 --name safety_v1

Afterwards the weights are copied to assets/models/<name>.pt and appear in
Settings → AI Detection Model as "Custom — <name>".
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from app.core.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


def train(
    data: str,
    base: str,
    epochs: int,
    imgsz: int,
    device: str,
    name: str,
    project: str,
    model_dir: str,
) -> int:
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics is not installed. Run: pip install ultralytics")
        return 1

    if data != "coco8.yaml" and not Path(data).exists():
        print(f"Dataset config not found: {data}\n"
              f"See datasets/README.md for the expected format.")
        return 1

    print(f"Fine-tuning {base} on {data} for {epochs} epochs (imgsz={imgsz}, "
          f"device={device})…")
    model = YOLO(base)
    results = model.train(
        data=data, epochs=epochs, imgsz=imgsz,
        device=(None if device == "auto" else device),
        project=project, name=name, exist_ok=True,
    )

    # Locate and publish the best weights.
    save_dir = Path(getattr(results, "save_dir", Path(project) / name))
    best = save_dir / "weights" / "best.pt"
    if not best.exists():
        print(f"Training finished but best.pt not found under {save_dir}.")
        return 1

    out_dir = Path(model_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    published = out_dir / f"{name}.pt"
    shutil.copy2(best, published)
    print(f"\n✓ Trained weights published to {published}")
    print("  Open the app → Settings → AI Detection Model → select "
          f"'Custom — {name}' → Apply & Save, then run Video Detection.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a custom YOLO model.")
    parser.add_argument("--data", required=True,
                        help="Path to dataset data.yaml (or 'coco8.yaml' for a smoke test).")
    parser.add_argument("--base", default="yolo11n.pt",
                        help="Base weights to fine-tune (e.g. yolo11n.pt, yolo11n-pose.pt).")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto", help="auto | cpu | cuda | 0")
    parser.add_argument("--name", default="custom_model",
                        help="Run name; weights publish to assets/models/<name>.pt.")
    parser.add_argument("--project", default="runs/train")
    parser.add_argument("--model-dir", default="assets/models")
    args = parser.parse_args(argv)

    configure_logging(level="INFO", console=True)
    return train(args.data, args.base, args.epochs, args.imgsz, args.device,
                 args.name, args.project, args.model_dir)


if __name__ == "__main__":
    sys.exit(main())
