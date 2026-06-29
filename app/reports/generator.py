"""Report generation.

Writes a human-readable text report capturing a snapshot of the platform
state (active profile, model, and current detection statistics). This is the
minimal Phase 12 surface; once the database lands, reports will aggregate
historical events over a date range. The function signature already accepts
the inputs that aggregation will need.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReportContext:
    """Inputs for a report. Decouples the generator from UI/state types."""

    report_type: str
    product_name: str
    profile: str
    model: str
    active_cameras: int = 0
    total_cameras: int = 0
    events_today: int = 0
    active_alerts: int = 0


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")


def generate_report(ctx: ReportContext, report_dir: str | Path,
                    when: float | None = None) -> Path:
    """Write a report file and return its path."""
    when = time.time() if when is None else when
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(when))
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_slug(ctx.report_type)}_{stamp}.txt"

    readable = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))
    lines = [
        f"{ctx.product_name} — {ctx.report_type} Report",
        "=" * 60,
        f"Generated      : {readable}",
        f"Active profile : {ctx.profile}",
        f"Detection model: {ctx.model}",
        "",
        "Snapshot",
        "-" * 60,
        f"Active cameras : {ctx.active_cameras}/{ctx.total_cameras}",
        f"Events today   : {ctx.events_today}",
        f"Active alerts  : {ctx.active_alerts}",
        "",
        "Note: historical event aggregation will be added once the database "
        "layer (Phase 11) is in place.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def list_reports(report_dir: str | Path) -> list[Path]:
    """Return existing report files, newest first."""
    out_dir = Path(report_dir)
    if not out_dir.is_dir():
        return []
    files = [p for p in out_dir.iterdir() if p.is_file() and p.suffix == ".txt"]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
