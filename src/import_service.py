"""Validate Excel register uploads before they reach the database."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10_000
MAX_COLUMNS = 100

REGISTER_RULES = {
    "enquiries": {
        "required_columns": [
            "Client Name",
            "Enq. No. & Date",
            "Item",
        ],
        "key_column": "Enq. No. & Date",
        "required_values": [
            "Client Name",
            "Enq. No. & Date",
            "Item",
        ],
        "date_columns": [
            "Enq. Rec. Date",
            "Due Date",
            "Qtn Date",
        ],
        "numeric_columns": ["Quotation Value"],
    },
    "quotations": {
        "required_columns": [
            "Quotation No.",
            "Client Name",
            "Items",
            "Remark",
            "WO No.",
            "Total Value",
        ],
        "key_column": "Quotation No.",
        "required_values": [
            "Quotation No.",
            "Client Name",
            "Items",
        ],
        "date_columns": ["Quotation Date"],
        "numeric_columns": ["Total Value"],
    },
}


def get_excel_sheets(file_bytes: bytes) -> list[str]:
    """Return sheet names after basic upload safety checks."""
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("The file exceeds the 10 MB upload limit.")

    try:
        workbook = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
        return workbook.sheet_names
    except Exception as exc:
        raise ValueError(
            "Could not read this Excel file. Upload a valid .xlsx workbook."
        ) from exc


def _cell_to_string(value: Any) -> str:
    """Normalize Excel cells while preserving identifiers as strings."""
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


def _record_key(value: Any) -> str:
    """Normalize identity fields for case-insensitive duplicate checks."""
    return _cell_to_string(value).strip().casefold()


def preview_excel(
    file_bytes: bytes,
    filename: str,
    register_type: str,
    sheet_name: str,
    existing_records: pd.DataFrame,
) -> dict[str, Any]:
    """
    Validate an Excel sheet and return a preview.

    This function never writes to the database.
    """
    if Path(filename).suffix.lower() != ".xlsx":
        raise ValueError(
            "Only .xlsx files are accepted. Macro-enabled files are not supported."
        )

    if register_type not in REGISTER_RULES:
        raise ValueError("Choose either the enquiries or quotations register.")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("The file exceeds the 10 MB upload limit.")

    rules = REGISTER_RULES[register_type]

    try:
        raw = pd.read_excel(
            BytesIO(file_bytes),
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=object,
        )
    except Exception as exc:
        raise ValueError("The selected worksheet could not be read.") from exc

    if raw.empty:
        raise ValueError("The selected worksheet contains no data rows.")

    if len(raw) > MAX_ROWS:
        raise ValueError(f"A maximum of {MAX_ROWS:,} rows is allowed.")

    if len(raw.columns) > MAX_COLUMNS:
        raise ValueError(f"A maximum of {MAX_COLUMNS} columns is allowed.")

    # Trim header whitespace and reject ambiguous column names.
    raw.columns = [str(column).strip() for column in raw.columns]

    if any(not column for column in raw.columns):
        raise ValueError("Every column must have a heading.")

    if len(set(raw.columns)) != len(raw.columns):
        raise ValueError("Duplicate column headings were found.")

    missing = sorted(set(rules["required_columns"]) - set(raw.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    # Ignore fully blank rows, but retain the original worksheet row number.
    raw = raw.dropna(how="all").copy()
    raw["_source_row"] = raw.index + 2

    if raw.empty:
        raise ValueError("No data rows were found.")

    errors: list[str] = []
    seen_keys: dict[str, int] = {}
    duplicate_rows: list[dict[str, Any]] = []
    cleaned_records: list[dict[str, str]] = []

    key_column = rules["key_column"]
    required_values = rules["required_values"]

    existing_keys = set()
    if key_column in existing_records.columns:
        existing_keys = {
            _record_key(value)
            for value in existing_records[key_column].tolist()
            if _record_key(value)
        }

    for _, row in raw.iterrows():
        source_row = int(row["_source_row"])
        record = {
            column: _cell_to_string(row[column])
            for column in raw.columns
            if column != "_source_row"
        }

        for field in required_values:
            if not record.get(field, "").strip():
                errors.append(f"Row {source_row}: '{field}' cannot be blank.")

        for field in rules["date_columns"]:
            value = record.get(field, "")
            if value:
                parsed = pd.to_datetime(value, errors="coerce")
                if pd.isna(parsed):
                    errors.append(f"Row {source_row}: '{field}' is not a valid date.")
                else:
                    record[field] = parsed.strftime("%Y-%m-%d")

        for field in rules["numeric_columns"]:
            value = record.get(field, "")
            if value:
                try:
                    number = float(value.replace(",", "").replace("₹", "").strip())
                    if number < 0:
                        raise ValueError
                    record[field] = str(number)
                except (ValueError, AttributeError):
                    errors.append(
                        f"Row {source_row}: '{field}' must be a "
                        "non-negative number or blank."
                    )

        key = _record_key(record.get(key_column, ""))

        if key:
            if key in existing_keys:
                duplicate_rows.append(
                    {
                        "Excel row": source_row,
                        "Record key": record[key_column],
                        "Reason": "Already exists in the database",
                    }
                )
            elif key in seen_keys:
                duplicate_rows.append(
                    {
                        "Excel row": source_row,
                        "Record key": record[key_column],
                        "Reason": (
                            f"Duplicate within this file; first seen at "
                            f"row {seen_keys[key]}"
                        ),
                    }
                )
            else:
                seen_keys[key] = source_row

        cleaned_records.append(record)

    preview = pd.DataFrame(cleaned_records)

    return {
        "register_type": register_type,
        "filename": Path(filename).name,
        "sheet_name": sheet_name,
        "row_count": len(cleaned_records),
        "preview": preview.head(20),
        "errors": errors,
        "duplicates": pd.DataFrame(
            duplicate_rows,
            columns=["Excel row", "Record key", "Reason"],
        ),
        "records": cleaned_records,
        "valid": not errors and not duplicate_rows,
    }
