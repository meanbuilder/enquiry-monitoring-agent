"""SQLite persistence for EnquiryPulse blockers and audit history.

This module contains database access only. It does not depend on Streamlit.
"""

import csv
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "enquirypulse.db"

BLOCKER_FIELDS = {
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

VALID_STATUSES = {"Open", "In Progress", "Resolved"}
VALID_PRIORITIES = {"Urgent", "High", "Medium", "Low"}


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a database connection with foreign-key enforcement."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(db_path),
        timeout=10,
        isolation_level="DEFERRED",
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize_database(
    csv_path: Path,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Create tables and seed synthetic CSV records only if the DB is empty."""
    csv_path = Path(csv_path)
    db_path = Path(db_path)

    with _connect(Path(db_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS blockers (
                blocker_id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                enquiry_reference TEXT NOT NULL,
                item TEXT NOT NULL,
                blocker TEXT NOT NULL,
                owner TEXT NOT NULL,
                due_date TEXT NOT NULL,
                estimated_value_inr REAL NOT NULL
                    CHECK (estimated_value_inr >= 0),
                status TEXT NOT NULL
                    CHECK (status IN ('Open', 'In Progress', 'Resolved')),
                priority TEXT NOT NULL
                    CHECK (priority IN ('Urgent', 'High', 'Medium', 'Low')),
                evidence TEXT NOT NULL,
                next_action TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS blocker_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                actor TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (blocker_id)
                    REFERENCES blockers(blocker_id)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_blocker_time
            ON blocker_audit(blocker_id, changed_at);
            """
        )

        existing_count = connection.execute("SELECT COUNT(*) FROM blockers").fetchone()[
            0
        ]

        # Do not overwrite changes or duplicate records on subsequent starts.
        if existing_count > 0:
            return

        if not csv_path.is_file():
            raise FileNotFoundError(f"Initial blocker CSV was not found: {csv_path}")

        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

        if not rows:
            return

        required = {"blocker_id"} | BLOCKER_FIELDS
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError(
                "Blocker CSV is missing columns: " + ", ".join(sorted(missing))
            )

        now = _utc_now()
        for row in rows:
            blocker_id = str(row["blocker_id"]).strip()
            if not blocker_id:
                raise ValueError("A blocker has an empty blocker_id.")

            status = str(row["status"]).strip()
            priority = str(row["priority"]).strip()
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status for {blocker_id}: {status}")
            if priority not in VALID_PRIORITIES:
                raise ValueError(f"Invalid priority for {blocker_id}: {priority}")

            try:
                value = float(row["estimated_value_inr"])
                if value < 0:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid estimated value for {blocker_id}.") from exc

            connection.execute(
                """
                INSERT INTO blockers (
                    blocker_id, client_name, enquiry_reference, item,
                    blocker, owner, due_date, estimated_value_inr,
                    status, priority, evidence, next_action, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    blocker_id,
                    str(row["client_name"]).strip(),
                    str(row["enquiry_reference"]).strip(),
                    str(row["item"]).strip(),
                    str(row["blocker"]).strip(),
                    str(row["owner"]).strip(),
                    str(row["due_date"]).strip(),
                    value,
                    status,
                    priority,
                    str(row["evidence"]).strip(),
                    str(row["next_action"]).strip(),
                    now,
                ),
            )


def list_blockers(
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return all blockers, with urgent and high-priority items first."""
    with _connect(Path(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT * FROM blockers
            ORDER BY
                CASE priority
                    WHEN 'Urgent' THEN 0
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    ELSE 3
                END,
                due_date,
                blocker_id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def update_blocker(
    blocker_id: str,
    changes: dict[str, Any],
    actor: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Update allowed fields and audit each changed value atomically."""
    if not blocker_id or not actor.strip():
        raise ValueError("A blocker ID and actor are required.")

    if not changes:
        raise ValueError("No changes were supplied.")

    unknown = set(changes) - BLOCKER_FIELDS
    if unknown:
        raise ValueError("Unsupported fields: " + ", ".join(sorted(unknown)))

    cleaned = {key: value for key, value in changes.items()}
    for field in (
        "client_name",
        "enquiry_reference",
        "item",
        "blocker",
        "owner",
        "due_date",
        "evidence",
        "next_action",
    ):
        if field in cleaned:
            cleaned[field] = str(cleaned[field]).strip()
            if not cleaned[field]:
                raise ValueError(f"{field} cannot be empty.")

    if "status" in cleaned and cleaned["status"] not in VALID_STATUSES:
        raise ValueError("Invalid blocker status.")

    if "priority" in cleaned and cleaned["priority"] not in VALID_PRIORITIES:
        raise ValueError("Invalid blocker priority.")

    if "estimated_value_inr" in cleaned:
        try:
            value = float(cleaned["estimated_value_inr"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Estimated value must be numeric.") from exc
        if value < 0:
            raise ValueError("Estimated value cannot be negative.")
        cleaned["estimated_value_inr"] = value

    timestamp = _utc_now()

    with _connect(Path(db_path)) as connection:
        current = connection.execute(
            "SELECT * FROM blockers WHERE blocker_id = ?",
            (blocker_id,),
        ).fetchone()

        if current is None:
            raise ValueError(f"Blocker not found: {blocker_id}")

        changed = []
        for field, new_value in cleaned.items():
            old_value = current[field]
            if str(old_value) != str(new_value):
                changed.append((field, str(old_value), str(new_value)))

        if not changed:
            return

        assignments = ", ".join(f"{field} = ?" for field in cleaned)
        values = list(cleaned.values())
        values.extend([timestamp, blocker_id])

        connection.execute(
            f"UPDATE blockers SET {assignments}, updated_at = ? WHERE blocker_id = ?",
            values,
        )

        connection.executemany(
            """
            INSERT INTO blocker_audit (
                blocker_id, field_name, old_value, new_value, actor, changed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (blocker_id, field, old, new, actor.strip(), timestamp)
                for field, old, new in changed
            ],
        )


def list_audit_history(
    blocker_id: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return audit records, optionally filtered to one blocker."""
    with _connect(Path(db_path)) as connection:
        if blocker_id:
            rows = connection.execute(
                """
                SELECT * FROM blocker_audit
                WHERE blocker_id = ?
                ORDER BY audit_id DESC
                """,
                (blocker_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM blocker_audit ORDER BY audit_id DESC"
            ).fetchall()

    return [dict(row) for row in rows]
