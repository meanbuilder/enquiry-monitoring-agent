"""Allowlisted, read-only tools for EnquiryPulse."""

import pandas as pd

ALLOWED_TOOLS = {
    "pipeline_summary",
    "priority_records",
    "search_records",
    "draft_followup",
    "decision_brief",
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
            "records": followups.head(0).copy(),
            "next_step": ("Review work-order checks and records marked Needs review."),
        }

    if tool_name == "priority_records":
        priority = str(args.get("priority", "High")).strip().title()

        if priority not in {"Urgent", "High", "Needs Review", "Normal"}:
            priority = "High"

        records = followups[
            followups["Priority"].str.casefold() == priority.casefold()
        ].copy()

        return {
            "tool": tool_name,
            "answer": (
                f"Python found {len(records)} record(s) with priority {priority}."
            ),
            "records": records,
            "evidence": {
                "priority": priority,
                "matching_records": len(records),
            },
            "next_step": ("Confirm ownership and timing with the responsible team."),
        }

    if tool_name == "search_records":
        query = str(args.get("query", "")).strip()

        if not query:
            return {
                "tool": tool_name,
                "answer": "Please specify a client, item, or reference.",
                "records": followups.head(0).copy(),
                "evidence": {},
                "next_step": "Enter a specific search term.",
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

        return {
            "tool": tool_name,
            "answer": f"Found {len(records)} record(s) matching '{query}'.",
            "records": records,
            "evidence": {
                "search_term": query,
                "matching_records": len(records),
            },
            "next_step": ("Verify matching records against the source register."),
        }

    if tool_name == "draft_followup":
        client = str(args.get("client_name", "")).strip()

        if not client:
            return {
                "tool": tool_name,
                "answer": "Please identify the client for the draft.",
                "records": followups.head(0).copy(),
                "evidence": {},
                "next_step": "Provide a client name.",
                "action_kind": "draft",
                "draft": "",
            }

        mask = (
            followups["Client Name"]
            .astype(str)
            .str.contains(client, case=False, na=False, regex=False)
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
            "next_step": ("Verify the record and review the draft before sending."),
            "action_kind": "draft",
        }

    records = (
        followups[followups["Priority"].isin(["Urgent", "High", "Needs review"])]
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
        "next_step": ("Review the evidence before approving an internal action."),
        "action_kind": "decision",
    }
