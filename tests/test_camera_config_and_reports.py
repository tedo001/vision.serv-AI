"""Tests for laptop-camera configuration and report generation."""

from __future__ import annotations

import types
from pathlib import Path

from app.camera.opencv_source import OpenCVCameraSource
from app.config.settings import CameraDefaults
from app.core.models import CameraSourceType
from app.reports.generator import ReportContext, generate_report, list_reports


# --- camera backend selection ----------------------------------------------
class _FakeCv2:
    CAP_ANY = 0
    CAP_DSHOW = 700
    CAP_AVFOUNDATION = 1200
    CAP_V4L2 = 200


def test_windows_uses_dshow_for_webcam() -> None:
    backend = OpenCVCameraSource.preferred_backend(
        _FakeCv2(), CameraSourceType.USB, platform="win32")
    assert backend == _FakeCv2.CAP_DSHOW


def test_macos_uses_avfoundation_for_webcam() -> None:
    backend = OpenCVCameraSource.preferred_backend(
        _FakeCv2(), CameraSourceType.USB, platform="darwin")
    assert backend == _FakeCv2.CAP_AVFOUNDATION


def test_linux_uses_v4l2_for_webcam() -> None:
    backend = OpenCVCameraSource.preferred_backend(
        _FakeCv2(), CameraSourceType.USB, platform="linux")
    assert backend == _FakeCv2.CAP_V4L2


def test_files_use_cap_any_regardless_of_platform() -> None:
    backend = OpenCVCameraSource.preferred_backend(
        _FakeCv2(), CameraSourceType.FILE, platform="win32")
    assert backend == _FakeCv2.CAP_ANY


def test_camera_defaults_include_resolution() -> None:
    cam = CameraDefaults.from_dict({"width": 1920, "height": 1080})
    assert cam.width == 1920 and cam.height == 1080
    assert CameraDefaults.from_dict({}).width == 1280  # sensible default


# --- report generation ------------------------------------------------------
def test_generate_report_writes_file(tmp_path: Path) -> None:
    ctx = ReportContext(report_type="Safety Compliance", product_name="AVP",
                        profile="construction", model="yolo26n",
                        active_cameras=2, total_cameras=3, events_today=5)
    path = generate_report(ctx, tmp_path, when=0.0)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Safety Compliance" in content
    assert "construction" in content
    assert "2/3" in content


def test_list_reports_newest_first(tmp_path: Path) -> None:
    ctx = ReportContext("Attendance", "AVP", "office", "yolo11n")
    p1 = generate_report(ctx, tmp_path, when=1000.0)
    p2 = generate_report(ctx, tmp_path, when=2000.0)
    listed = list_reports(tmp_path)
    assert listed[0] == p2 and p1 in listed


def test_list_reports_empty_dir(tmp_path: Path) -> None:
    assert list_reports(tmp_path / "nope") == []
