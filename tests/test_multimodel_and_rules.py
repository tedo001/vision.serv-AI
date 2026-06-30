"""Tests for multi-model detection, ByteTrack ids, and the rule engine."""

from __future__ import annotations

import types
from pathlib import Path

import numpy as np

from app.config.manager import ConfigManager
from app.core.models import BoundingBox, Detection, EventSeverity
from app.detection.composite import CompositeDetector
from app.detection.model_catalog import MODELS
from app.detection.yolo_detector import YoloDetector
from app.rules.builtins import (
    fire_smoke_rule,
    max_occupancy_rule,
    no_ppe_rule,
    restricted_zone_rule,
)
from app.rules.context import RuleContext
from app.rules.engine import RuleEngine
from app.rules.loader import load_rules_from_dir


def _ctx(dets, w=100, h=100, ts=1.0) -> RuleContext:
    return RuleContext(tuple(dets), w, h, "cam0", "construction", ts)


def _det(label, *, box=BoundingBox(0, 0, 10, 10), conf=0.9) -> Detection:
    return Detection(label, conf, box, "m")


# --- catalog ----------------------------------------------------------------
def test_new_model_variants_and_loaders() -> None:
    assert MODELS["yolo11n-seg"].task == "segment"
    assert MODELS["rtdetr-l"].loader == "rtdetr"
    assert MODELS["sam2-b"].loader == "sam"
    assert MODELS["yolo26s"].task == "detect"


# --- composite (multi-model) ------------------------------------------------
class _StubDetector:
    def __init__(self, name, labels):
        self._name = name
        self._labels = labels
        self.loaded = False

    @property
    def name(self):
        return self._name

    def load(self):
        self.loaded = True

    def detect(self, frame):
        return [_det(l) for l in self._labels]

    def unload(self):
        pass


def test_composite_merges_all_detectors() -> None:
    a = _StubDetector("objects", ["person", "truck"])
    b = _StubDetector("pose", ["person"])
    comp = CompositeDetector([a, b], name="objects+pose")
    comp.load()
    out = comp.detect(object())
    assert a.loaded and b.loaded
    assert [d.label for d in out] == ["person", "truck", "person"]
    assert comp.name == "objects+pose"


# --- ByteTrack id mapping ---------------------------------------------------
def test_detector_maps_track_id() -> None:
    det = YoloDetector("yolo26n", track=True)
    det._model = object()
    box = types.SimpleNamespace(
        xyxy=[np.array([0, 0, 10, 10], float)], cls=[0], conf=[0.9],
        id=[np.array(7.0)])
    result = types.SimpleNamespace(names={0: "person"}, boxes=[box], keypoints=None)
    out = det._map_results([result])
    assert out[0].track_id == 7


# --- rule builtins ----------------------------------------------------------
def test_no_ppe_rule_fires_on_missing_helmet() -> None:
    results = no_ppe_rule()(_ctx([_det("no_helmet"), _det("person")]))
    assert any(r.event_type == "ppe_no_helmet" and r.severity == EventSeverity.HIGH
               for r in results)


def test_fire_smoke_rule() -> None:
    results = fire_smoke_rule()(_ctx([_det("fire")]))
    assert results[0].event_type == "fire"
    assert results[0].severity == EventSeverity.CRITICAL


def test_max_occupancy_rule() -> None:
    crowd = [_det("person") for _ in range(6)]
    assert max_occupancy_rule(5)(_ctx(crowd))           # 6 > 5 -> fires
    assert max_occupancy_rule(10)(_ctx(crowd)) == []     # 6 <= 10 -> silent


def test_restricted_zone_rule_uses_frame_fractions() -> None:
    # Person centered at (50,50) in a 100x100 frame; zone covers the center.
    inside = _det("person", box=BoundingBox(45, 45, 55, 55))
    outside = _det("person", box=BoundingBox(0, 0, 5, 5))
    rule = restricted_zone_rule(0.25, 0.25, 0.75, 0.75)
    results = rule(_ctx([inside, outside]))
    assert len(results) == 1 and results[0].event_type == "restricted_zone"


# --- rule engine debounce + events ------------------------------------------
def test_rule_engine_debounces_and_publishes() -> None:
    received = []
    engine = RuleEngine((fire_smoke_rule(),), cooldown_seconds=10.0,
                        sinks=(types.SimpleNamespace(handle_event=received.append),))
    first = engine.evaluate(_ctx([_det("fire")], ts=100.0))
    assert len(first) == 1
    again = engine.evaluate(_ctx([_det("fire")], ts=105.0))   # within cooldown
    assert again == []
    later = engine.evaluate(_ctx([_det("fire")], ts=111.0))   # after cooldown
    assert len(later) == 1
    assert len(received) == 2


def test_bad_rule_does_not_crash_engine() -> None:
    def boom(ctx):
        raise RuntimeError("bad rule")
    engine = RuleEngine((boom, fire_smoke_rule()))
    events = engine.evaluate(_ctx([_det("fire")]))
    assert len(events) == 1  # good rule still ran


# --- custom rule loading ----------------------------------------------------
def test_load_custom_rules_from_dir(tmp_path: Path) -> None:
    (tmp_path / "my_rule.py").write_text(
        "from app.core.models import EventSeverity\n"
        "from app.rules.context import RuleResult\n"
        "def r(ctx):\n"
        "    return [RuleResult('custom_hit', EventSeverity.LOW, 'hi')] if ctx.detections else []\n"
        "RULES = [r]\n",
        encoding="utf-8",
    )
    rules = load_rules_from_dir(tmp_path)
    assert len(rules) == 1
    out = rules[0](_ctx([_det("person")]))
    assert out[0].event_type == "custom_hit"


# --- multi-model config -----------------------------------------------------
def test_effective_models_and_persistence(tmp_path: Path) -> None:
    mgr = ConfigManager(tmp_path / "d.yaml", overrides_path=tmp_path / "l.yaml")
    mgr.load()
    # No enabled_models -> falls back to active model.
    assert mgr.config.detection.effective_models == (mgr.config.detection.active_model,)
    mgr.update_detection(enabled_models=("yolo26n", "yolo11n-pose"), track=True)
    reloaded = ConfigManager(tmp_path / "d.yaml", overrides_path=tmp_path / "l.yaml").load()
    assert reloaded.detection.effective_models == ("yolo26n", "yolo11n-pose")
    assert reloaded.detection.track is True
