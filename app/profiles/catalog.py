"""Declarative industry-profile catalog (data only).

This is the *seed data* for the industry profile system. It lists each
vertical and the AI modules it enables, exactly as specified by the product.
It is pure, framework-agnostic data with no behaviour, so both the UI (to
render profile cards and module lists) and the Phase 6 profile **engine** (to
load models, rules, dashboards, and alert policies) read from one source.

Phase 6 will build the engine that turns a selected profile into a live
configuration; this module is the contract it builds upon.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndustryProfile:
    key: str
    display_name: str
    description: str
    modules: tuple[str, ...]


PROFILES: dict[str, IndustryProfile] = {
    "construction": IndustryProfile(
        key="construction",
        display_name="Construction Site",
        description="PPE compliance, heavy-machinery and fall/fire safety on site.",
        modules=(
            "Person Detection",
            "Helmet Detection",
            "Safety Vest Detection",
            "Gloves Detection",
            "Safety Boots Detection",
            "Machinery Detection",
            "Crane Detection",
            "Vehicle Detection",
            "Restricted Zone Detection",
            "Fall Detection",
            "Fire Detection",
            "Smoke Detection",
            "Worker Counting",
            "Attendance",
            "Safety Analytics",
        ),
    ),
    "classroom": IndustryProfile(
        key="classroom",
        display_name="Classroom",
        description="Attendance, engagement and safety monitoring in classrooms.",
        modules=(
            "Student Attendance",
            "Teacher Attendance",
            "Occupancy",
            "Mobile Phone Detection",
            "Sleeping Student Detection",
            "Fighting Detection",
            "Crowd Monitoring",
            "Emergency Detection",
            "Classroom Analytics",
        ),
    ),
    "office": IndustryProfile(
        key="office",
        display_name="Office",
        description="Attendance, occupancy and restricted-area monitoring.",
        modules=(
            "Employee Attendance",
            "Visitor Detection",
            "Occupancy",
            "Restricted Area Monitoring",
            "Fire Detection",
            "Smoke Detection",
            "Meeting Room Analytics",
        ),
    ),
    "hospital": IndustryProfile(
        key="hospital",
        display_name="Hospital",
        description="Staff/patient monitoring, PPE and emergency safety.",
        modules=(
            "Staff Attendance",
            "Patient Monitoring",
            "PPE Detection",
            "Restricted Area Detection",
            "Fall Detection",
            "Emergency Monitoring",
            "Fire Detection",
            "Smoke Detection",
        ),
    ),
    "warehouse": IndustryProfile(
        key="warehouse",
        display_name="Warehouse",
        description="Forklift safety, PPE, intrusion and inventory analytics.",
        modules=(
            "Forklift Detection",
            "Worker Detection",
            "PPE Detection",
            "Box Counting",
            "Intrusion Detection",
            "Fire Detection",
            "Smoke Detection",
            "Inventory Analytics",
        ),
    ),
    "factory": IndustryProfile(
        key="factory",
        display_name="Factory",
        description="Machine safety, PPE, productivity and restricted areas.",
        modules=(
            "PPE Detection",
            "Machine Safety",
            "Worker Counting",
            "Equipment Monitoring",
            "Fire Detection",
            "Smoke Detection",
            "Restricted Area Detection",
            "Productivity Analytics",
        ),
    ),
    "retail": IndustryProfile(
        key="retail",
        display_name="Retail",
        description="Footfall, queues, shelf monitoring and loss prevention.",
        modules=(
            "Customer Counting",
            "Queue Monitoring",
            "Shelf Monitoring",
            "Theft Detection",
            "Occupancy Analytics",
            "Fire Detection",
        ),
    ),
}


def get_profile(key: str) -> IndustryProfile | None:
    """Return the profile for ``key`` (case-insensitive), or None."""
    return PROFILES.get(key.lower())
