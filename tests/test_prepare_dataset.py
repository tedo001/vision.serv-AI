"""Tests for the dataset preparation tool."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.prepare_dataset import prepare


def _make_raw(tmp_path: Path, n: int = 10) -> Path:
    src = tmp_path / "raw"
    src.mkdir()
    for i in range(n):
        (src / f"img{i}.jpg").write_bytes(b"x")
        # Half the images have labels; half are background.
        if i % 2 == 0:
            (src / f"img{i}.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    return src


def test_prepare_builds_split_and_yaml(tmp_path: Path) -> None:
    src = _make_raw(tmp_path, 10)
    out = tmp_path / "ds"
    summary = prepare(src, out, ["person", "helmet"], val_split=0.2, seed=1)

    assert summary["total_images"] == 10
    assert summary["train"] + summary["val"] == 10
    assert summary["val"] >= 1

    # Folders exist and contain the right counts.
    train_imgs = list((out / "images/train").glob("*.jpg"))
    val_imgs = list((out / "images/val").glob("*.jpg"))
    assert len(train_imgs) == summary["train"]
    assert len(val_imgs) == summary["val"]

    # data.yaml is valid and trainable-shaped.
    data = yaml.safe_load((out / "data.yaml").read_text(encoding="utf-8"))
    assert data["train"] == "images/train"
    assert data["val"] == "images/val"
    assert data["names"] == {0: "person", 1: "helmet"}


def test_labels_copied_only_when_present(tmp_path: Path) -> None:
    src = _make_raw(tmp_path, 10)
    out = tmp_path / "ds"
    prepare(src, out, ["person"], val_split=0.3, seed=2)
    # Every label file present in output must correspond to an image.
    all_labels = list((out / "labels/train").glob("*.txt")) + \
        list((out / "labels/val").glob("*.txt"))
    assert len(all_labels) == 5  # exactly the 5 labeled source images


def test_rejects_empty_source(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        prepare(empty, tmp_path / "ds", ["person"])


def test_rejects_no_names(tmp_path: Path) -> None:
    src = _make_raw(tmp_path, 3)
    with pytest.raises(ValueError):
        prepare(src, tmp_path / "ds", [])
