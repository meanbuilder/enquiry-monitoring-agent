
"""Allowlisted, read-only tools for EnquiryPulse."""

import re
from datetime import datetime

import pandas as pd

ALLOWED_TOOLS = {
    "pipeline_summary",
    "priority_records",
    "search_records",
    "draft_followup",
    "decision_brief",
}


def _empty_records(records: pd.DataFrame) -> pd.DataFrame:
    return records.head(0).copy()


def _parse_date_query(query: str):
    """Return a date filter when the query contains a supported date condition."""

    pattern = (
        r"\b(after|before|on|since|from)\s+"
        r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}|"
        r"\d{4}-\d{2}-\d{2}|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}|"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}|"
        r"\d{4})\b"
    )

    match = re.search(pattern, query, flags=re.IGNORECASE)
    if not match:
        return None

    operator, date_text = match.groups()

    parsed = pd.to_datetime(date_text, errors="coerce", dayfirst=True)

    if pd.isna(parsed):
        return None

    return operator.casefold(), pd.Timestamp(parsed).normalize()


def _find_date_column(records: pd.DataFrame):
    """Prefer the quotation date when searching quotation records."""

    for column in ("Quotation Date", "Qtn Date", "Quotation Date and Date"):
        if column in records.columns:
            return column

    return None


def _search_records(query: str, followups: pd.DataFrame):
    """Search records by date condition or literal text."""

    date_filter = _parse_date_query(query)

    if date_filter:
        operator, target_date = date_filter
        date_column = _find_date_column(followups)

        if date_column is not None:
            dates = pd.to_datetime(
                followups[date_column], errors="coerce", dayfirst=True
            ).dt.normalize()

            if operator == "after":
                mask = dates > target_date
            elif operator == "before":
                mask = dates < target_date
            else:
                mask = dates >= target_date

            records = followups[mask.fillna(False)].copy()
            return records, {
                "search_term": query,
                "filter_type": "date",
                "date_column": date_column,
                "operator": operator,
                "target_date": target_date.strftime("%Y-%m-%d"),
                "matching_records": len(records),
            }

    mask = (
        followups.astype(str)
        .apply(
            lambda column: column.str.contains(
                query, case=False, na=False, regex=False
            )
        )
        .any(axis=1)
    )

    records = followups[mask].copy()

    return records, {
        "search_term": query,
        "filter_type": "text",
        "matching_records": len(records),
    }


def execute_tool(
    tool_name: str,
    args: dict,
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
    followups: pd.DataFrame,
    metrics: dict,
) -> dict:
    """Execute only approved analysis tools."""

    args = args if isinstance(args, dict) else {}

    if tool_name not in ALLOWED_TOOLS:
        tool_name = "pipeline_summary"

    if tool_name == "pipeline_summary":
        return {
            "tool": tool_name,
            "answer": "Pipeline metrics calculated by Python.",
            "evidence": dict(metrics),
            "records": _empty_records(followups),
            "next_step": "Review work-order checks and records marked Needs review.",
        }

    if tool_name == "priority_records":
        priority = str(args.get("priority", "High")).strip().title()

        if priority not in {"Urgent", "High", "Needs Review", "Normal"}:
            priority = "High"

        records = followups[
            followups["Priority"].astype(str).str.casefold()
            == priority.casefold()
        ].copy()

        return {
            "tool": tool_name,
            "answer": f"Python found {len(records)} record(s) with priority {priority}.",
            "records": records,
            "evidence": {
                "priority": priority,
                "matching_records": len(records),
            },
            "next_step": "Confirm ownership and timing with the responsible team.",
        }

    if tool_name == "search_records":
        query = str(args.get("query", "")).strip()

        if not query:
            return {
                "tool": tool_name,
                "answer": "Please specify a client, item, reference, or date condition.",
                "records": _empty_records(followups),
                "evidence": {},
                "next_step": "Enter a specific search term.",
            }

        records, evidence = _search_records(query, followups)

        return {
            "tool": tool_name,
            "answer": f"Found {len(records)} record(s) matching '{query}'.",
            "records": records,
            "evidence": evidence,
            "next_step": "Verify matching records against the source register.",
        }

    if tool_name == "draft_followup":
        client = str(args.get("client_name", "")).strip()

        if not client:
            return {
                "tool": tool_name,
                "answer": "Please identify the client for the draft.",
                "records": _empty_records(followups),
                "evidence": {},
                "next_step": "Provide a client name.",
                "action_kind": "draft",
                "draft": "",
            }

        mask = followups["Client Name"].astype(str).str.contains(
            client, case=False, na=False, regex=False
        )
        records = followups[mask].copy()

        return {
            "tool": tool_name,
            "answer": f"Found {len(records)} record(s) for {client}.",
            "records": records,
            "evidence": {
                "client_name": client,
                "matching_records": len(records),
            },
            "next_step": "Verify the record and review the draft before sending.",
            "action_kind": "draft",
        }

    records = (
        followups[
            followups["Priority"].astype(str).str.casefold().isin(
                ["urgent", "high", "needs review"]
            )
        ]
        .head(10)
        .copy()
    )

    return {
        "tool": "decision_brief",
        "answer": (
            f"Prepared a decision brief from {len(records)} high-attention record(s)."
        ),
        "records": records,
        "evidence": {
            "question": str(args.get("question", "")),
            "records_considered": len(records),
        },
        "next_step": "Review the evidence before approving an internal action.",
        "action_kind": "decision",
    }
