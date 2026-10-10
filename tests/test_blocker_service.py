"""Tests for blocker validation and business calculations."""

from pathlib import Path

import pandas as pd
import pytest

from src.blocker_service import build_blocker_overview, load_blockers

ROOT = Path(__file__).resolve().parents[1]
BLOCKER_FILE = ROOT / "sample_data" / "blockers.csv"


def test_demo_blocker_register_loads_and_validates():
    blockers = load_blockers(BLOCKER_FILE)

    assert len(blockers) == 8
    assert blockers["blocker_id"].is_unique
    assert set(blockers["status"]) <= {"Open", "In Progress", "Resolved"}


def test_overview_excludes_resolved_blockers_from_exposure():
    blockers = load_blockers(BLOCKER_FILE)

    overview = build_blocker_overview(blockers, as_of="2026-10-10")

    assert overview["total_blockers"] == 8
    assert overview["active_blockers"] == 7
    assert overview["resolved_blockers"] == 1
    assert overview["overdue_blockers"] == 3
    assert overview["estimated_exposure_inr"] == 3_200_000


def test_invalid_due_date_is_rejected():
    blockers = load_blockers(BLOCKER_FILE)
    blockers.loc[0, "due_date"] = "not-a-date"

    with pytest.raises(ValueError, match="due dates"):
        build_blocker_overview(blockers, as_of="2026-10-10")


def test_negative_estimated_value_is_rejected():
    blockers = load_blockers(BLOCKER_FILE)
    blockers.loc[0, "estimated_value_inr"] = -100

    with pytest.raises(ValueError, match="non-negative"):
        build_blocker_overview(blockers, as_of="2026-10-10")
