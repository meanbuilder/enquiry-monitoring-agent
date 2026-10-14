from pathlib import Path

import pytest

from src.blocker_repository import (
    initialize_database,
    list_audit_history,
    list_blockers,
    update_blocker,
)

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "sample_data" / "blockers.csv"


@pytest.fixture
def database(tmp_path):
    db_path = tmp_path / "test.db"
    initialize_database(CSV_PATH, db_path)
    return db_path


def test_initialization_loads_demo_blockers(database):
    blockers = list_blockers(database)
    assert len(blockers) == 8


def test_updates_persist_and_create_audit_records(database):
    update_blocker(
        "BLK-001",
        {"status": "In Progress", "owner": "Asha Mehta"},
        actor="demo-admin",
        db_path=database,
    )

    blocker = next(
        item for item in list_blockers(database) if item["blocker_id"] == "BLK-001"
    )

    assert blocker["status"] == "In Progress"

    audit = list_audit_history("BLK-001", database)
    assert len(audit) == 1
    assert audit[0]["field_name"] == "status"
    assert audit[0]["old_value"] == "Open"
    assert audit[0]["new_value"] == "In Progress"


def test_reinitialization_does_not_overwrite_changes(database):
    update_blocker(
        "BLK-001",
        {"status": "Resolved"},
        actor="demo-admin",
        db_path=database,
    )

    initialize_database(CSV_PATH, database)

    blocker = next(
        item for item in list_blockers(database) if item["blocker_id"] == "BLK-001"
    )
    assert blocker["status"] == "Resolved"


def test_invalid_priority_is_rejected(database):
    with pytest.raises(ValueError, match="priority"):
        update_blocker(
            "BLK-001",
            {"priority": "Critical"},
            actor="demo-admin",
            db_path=database,
        )


def test_failed_update_does_not_change_blocker(database):
    before = next(
        item for item in list_blockers(database) if item["blocker_id"] == "BLK-001"
    )

    with pytest.raises(ValueError):
        update_blocker(
            "BLK-001",
            {"status": "Invalid Status"},
            actor="demo-admin",
            db_path=database,
        )

    after = next(
        item for item in list_blockers(database) if item["blocker_id"] == "BLK-001"
    )
    assert after["status"] == before["status"]
    assert list_audit_history("BLK-001", database) == []
