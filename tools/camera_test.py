"""Laptop-camera test utility (no GUI required).

Verifies that a camera works and measures basic capture performance from the
terminal — handy on machines where opening the full desktop UI is awkward, or
to confirm the lap cam before running detection.

Usage:
    python -m tools.camera_test --scan
    python -m tools.camera_test --index 0 --frames 60
    python -m tools.camera_test --index 0 --snapshot

Exits 0 on success, 1 on failure (so it is CI/script friendly).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from app.camera.diagnostics import list_cameras, probe_camera
from app.camera.opencv_source import OpenCVCameraSource
from app.core.exceptions import CameraError
from app.core.logging_config import configure_logging, get_logger
from app.core.models import CameraSourceType

logger = get_logger(__name__)


def _scan() -> int:
    found = list_cameras(max_index=5)
    if not found:
        print("No cameras found on indices 0–5.")
        return 1
    print("Available cameras:")
    for probe in found:
        print(f"  • index {probe.index}: {probe.width}×{probe.height}")
    return 0


def _capture(index: int, frames: int, snapshot: bool) -> int:
    probe = probe_camera(index)
    if not probe.available:
        print(f"Camera {index} not available: {probe.message}")
        return 1
    print(f"Camera {index} opened at {probe.width}×{probe.height}. "
          f"Capturing {frames} frames…")

    source = OpenCVCameraSource(index, camera_id=f"webcam{index}",
                                source_type=CameraSourceType.USB)
    source.open()
    captured = 0
    last_frame = None
    start = time.time()
    try:
        while captured < frames:
            frame = source.read()
            if frame is None:
                print("Frame read failed; stopping early.")
                break
            last_frame = frame
            captured += 1
    finally:
        source.release()

    elapsed = max(time.time() - start, 1e-6)
    fps = captured / elapsed
    print(f"Captured {captured} frames in {elapsed:.2f}s  →  {fps:.1f} FPS")

    if snapshot and last_frame is not None:
        out_dir = Path("screenshots")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"camera_test_{index}.jpg"
        try:
            import cv2
            cv2.imwrite(str(out_path), last_frame.image)
            print(f"Saved snapshot to {out_path}")
        except Exception as exc:  # noqa: BLE001
            print(f"Could not save snapshot: {exc}")
            return 1
    return 0 if captured > 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test a laptop/USB camera.")
    parser.add_argument("--scan", action="store_true",
                        help="List available camera indices and exit.")
    parser.add_argument("--index", type=int, default=0,
                        help="Camera index to test (0 = built-in lap cam).")
    parser.add_argument("--frames", type=int, default=30,
                        help="Number of frames to capture for the FPS test.")
    parser.add_argument("--snapshot", action="store_true",
                        help="Save one captured frame to screenshots/.")
    args = parser.parse_args(argv)

    configure_logging(level="INFO", console=True)
    try:
        if args.scan:
            return _scan()
        return _capture(args.index, args.frames, args.snapshot)
    except CameraError as exc:
        print(f"Camera error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
