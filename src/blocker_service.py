"""Business rules for EnquiryPulse blocker records."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "blocker_id",
    "client_name",
    "enquiry_reference",
    "item",
    "blocker",
    "owner",
    "due_date",
    "estimated_value_inr",
    "status",
    "priority",
    "evidence",
    "next_action",
}

ACTIVE_STATUSES = {"Open", "In Progress"}
VALID_STATUSES = ACTIVE_STATUSES | {"Resolved"}
VALID_PRIORITIES = {"Urgent", "High", "Medium", "Low"}

PRIORITY_ORDER = {
    "Urgent": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def load_blockers(path: str | Path) -> pd.DataFrame:
    """Load and validate the blocker register from CSV."""
    csv_path = Path(path)

    if not csv_path.is_file():
        raise FileNotFoundError(f"Blocker register not found: {csv_path}")

    blockers = pd.read_csv(csv_path)

    missing = REQUIRED_COLUMNS - set(blockers.columns)
    if missing:
        raise ValueError(
            f"Blocker register is missing columns: {', '.join(sorted(missing))}"
        )

    if blockers.empty:
        raise ValueError("Blocker register contains no records.")

    for column in REQUIRED_COLUMNS:
        if blockers[column].isna().any():
            raise ValueError(f"Blocker register contains blank values in '{column}'.")

        if blockers[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Blocker register contains blank values in '{column}'.")

    if blockers["blocker_id"].duplicated().any():
        raise ValueError("Blocker IDs must be unique.")

    blockers["status"] = blockers["status"].astype(str).str.strip()
    invalid_statuses = set(blockers["status"]) - VALID_STATUSES
    if invalid_statuses:
        raise ValueError(f"Invalid blocker status values: {sorted(invalid_statuses)}")

    blockers["priority"] = blockers["priority"].astype(str).str.strip()
    invalid_priorities = set(blockers["priority"]) - VALID_PRIORITIES
    if invalid_priorities:
        raise ValueError(
            f"Invalid blocker priority values: {sorted(invalid_priorities)}"
        )

    blockers["due_date"] = pd.to_datetime(
        blockers["due_date"], errors="coerce"
    ).dt.normalize()

    if blockers["due_date"].isna().any():
        raise ValueError("Blocker due dates must be valid dates.")

    blockers["estimated_value_inr"] = pd.to_numeric(
        blockers["estimated_value_inr"], errors="coerce"
    )

    if (
        blockers["estimated_value_inr"].isna().any()
        or (blockers["estimated_value_inr"] < 0).any()
    ):
        raise ValueError("Estimated values must be non-negative numbers.")

    return blockers


def build_blocker_overview(
    blockers: pd.DataFrame,
    as_of: str | pd.Timestamp | None = None,
) -> dict:
    """Calculate an evidence-oriented summary of the blocker register."""
    if blockers.empty:
        raise ValueError("Cannot summarize an empty blocker register.")

    required = REQUIRED_COLUMNS
    missing = required - set(blockers.columns)
    if missing:
        raise ValueError(
            f"Blocker data is missing columns: {', '.join(sorted(missing))}"
        )

    today = (
        pd.Timestamp(as_of).normalize()
        if as_of is not None
        else pd.Timestamp.now().normalize()
    )

    data = blockers.copy()
    data["due_date"] = pd.to_datetime(data["due_date"], errors="coerce").dt.normalize()
    data["estimated_value_inr"] = pd.to_numeric(
        data["estimated_value_inr"], errors="coerce"
    )

    if data["due_date"].isna().any():
        raise ValueError("Blocker due dates must be valid dates.")

    if (
        data["estimated_value_inr"].isna().any()
        or (data["estimated_value_inr"] < 0).any()
    ):
        raise ValueError("Estimated values must be non-negative numbers.")

    active = data[data["status"].isin(ACTIVE_STATUSES)].copy()
    overdue = active[active["due_date"] < today].copy()

    active["_priority_order"] = active["priority"].map(PRIORITY_ORDER)
    active = active.sort_values(["_priority_order", "due_date", "blocker_id"]).drop(
        columns="_priority_order"
    )

    overdue_ids = set(overdue["blocker_id"])

    return {
        "total_blockers": len(data),
        "active_blockers": len(active),
        "overdue_blockers": len(overdue),
        "resolved_blockers": int((data["status"] == "Resolved").sum()),
        "estimated_exposure_inr": float(active["estimated_value_inr"].sum()),
        "overdue_blocker_ids": overdue_ids,
        "attention": active.reset_index(drop=True),
    }
