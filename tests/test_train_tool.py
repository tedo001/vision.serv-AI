"""Tests for the training tool's dataset resolution and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from tools.train import _resolve_and_check


def _write_yaml(path: Path) -> None:
    path.write_text(
        "path: .\ntrain: images/train\nval: images/val\nnames:\n  0: person\n",
        encoding="utf-8",
    )


def test_reports_missing_image_folders(tmp_path: Path) -> None:
    cfg = tmp_path / "data.yaml"
    _write_yaml(cfg)
    resolved, problems = _resolve_and_check(str(cfg))
    # Both splits missing -> clear problems, not a crash.
    assert any("train" in p for p in problems)
    assert any("val" in p for p in problems)


def test_reports_empty_folders(tmp_path: Path) -> None:
    cfg = tmp_path / "data.yaml"
    _write_yaml(cfg)
    (tmp_path / "images/train").mkdir(parents=True)
    (tmp_path / "images/val").mkdir(parents=True)
    _, problems = _resolve_and_check(str(cfg))
    assert all("no images" in p for p in problems)
    assert len(problems) == 2


def test_valid_dataset_resolves_absolute_path(tmp_path: Path) -> None:
    cfg = tmp_path / "data.yaml"
    _write_yaml(cfg)
    for split in ("train", "val"):
        d = tmp_path / "images" / split
        d.mkdir(parents=True)
        (d / "img1.jpg").write_bytes(b"x")
    resolved, problems = _resolve_and_check(str(cfg))
    assert problems == []
    # The resolved YAML carries an absolute dataset root (fixes path: . bug).
    data = yaml.safe_load(Path(resolved).read_text(encoding="utf-8"))
    assert Path(data["path"]).is_absolute()
    assert Path(data["path"]) == tmp_path.resolve()


def test_missing_yaml_reported(tmp_path: Path) -> None:
    resolved, problems = _resolve_and_check(str(tmp_path / "nope.yaml"))
    assert resolved is None and problems
