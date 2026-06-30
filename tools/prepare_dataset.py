"""Turn a flat folder of images + YOLO labels into a trainable dataset.

This is the missing step between "I have labeled images" and "I can run
tools/train.py". Point it at a folder containing image files and their
matching ``.txt`` YOLO label files; it creates the train/val split layout
Ultralytics expects and writes a ready ``data.yaml``.

Example
-------
    python -m tools.prepare_dataset --src D:\\raw_labeled --out datasets\\safety \\
        --names person,helmet,no_helmet,safety_vest --val 0.2

Then:
    python -m tools.train --data datasets/safety/data.yaml --base yolo11n.pt --epochs 100 --name safety_v1
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

import yaml

from app.core.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def prepare(
    src: str | Path,
    out: str | Path,
    names: list[str],
    *,
    val_split: float = 0.2,
    seed: int = 0,
) -> dict:
    """Build a YOLO dataset under ``out`` from images+labels in ``src``.

    Returns a summary dict. Images without a matching ``.txt`` are kept as
    background (negative) samples, which is valid in YOLO.
    """
    src_dir = Path(src)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"source folder not found: {src_dir}")
    if not names:
        raise ValueError("provide at least one class name via --names")
    if not 0.0 < val_split < 1.0:
        raise ValueError("--val must be between 0 and 1 (exclusive)")

    images = sorted(p for p in src_dir.rglob("*") if p.suffix.lower() in _IMAGE_EXTS)
    if not images:
        raise FileNotFoundError(f"no images found under {src_dir}")

    rng = random.Random(seed)
    rng.shuffle(images)
    cut = max(1, int(len(images) * (1 - val_split)))
    splits = {"train": images[:cut], "val": images[cut:] or images[:1]}

    out_dir = Path(out)
    for split, files in splits.items():
        img_out = out_dir / "images" / split
        lbl_out = out_dir / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)
        for img in files:
            shutil.copy2(img, img_out / img.name)
            label = img.with_suffix(".txt")
            if label.exists():
                shutil.copy2(label, lbl_out / label.name)

    data_yaml = out_dir / "data.yaml"
    data_yaml.write_text(
        yaml.safe_dump({
            "path": ".",
            "train": "images/train",
            "val": "images/val",
            "names": {i: n for i, n in enumerate(names)},
        }, sort_keys=False),
        encoding="utf-8",
    )

    summary = {
        "total_images": len(images),
        "train": len(splits["train"]),
        "val": len(splits["val"]),
        "classes": names,
        "data_yaml": str(data_yaml),
    }
    logger.info("Prepared dataset: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a YOLO train/val dataset.")
    parser.add_argument("--src", required=True, help="Folder of images + .txt labels.")
    parser.add_argument("--out", required=True, help="Output dataset folder.")
    parser.add_argument("--names", required=True,
                        help="Comma-separated class names (order = class id).")
    parser.add_argument("--val", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    configure_logging(level="INFO", console=True)
    names = [n.strip() for n in args.names.split(",") if n.strip()]
    try:
        summary = prepare(args.src, args.out, names, val_split=args.val, seed=args.seed)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    print(f"\n✓ Dataset ready: {summary['train']} train / {summary['val']} val "
          f"images, {len(names)} classes.")
    print(f"  Train it:  python -m tools.train --data {summary['data_yaml']} "
          f"--base yolo11n.pt --epochs 100 --name my_model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
