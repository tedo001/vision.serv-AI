"""Reporting layer (Phase 12, minimal).

Generates operational report files (safety, attendance, events summary, …)
into the configured ``report_dir``. The generator is framework-agnostic and
testable; the UI only collects parameters and lists the output.
"""

from __future__ import annotations

from app.reports.generator import generate_report, list_reports

__all__ = ["generate_report", "list_reports"]
