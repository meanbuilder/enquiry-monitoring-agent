
"""Rule-based enquiry assistant with optional OpenAI explanations."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


def answer_demo_question(
    question: str,
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
    followups: pd.DataFrame,
    metrics: dict,
) -> dict:
    """Analyse records using existing Python business rules."""

    question = (question or "").strip().lower()

    # Always return the structure required by app.py.
    empty_result = {
        "answer": "",
        "records": pd.DataFrame(),
        "next_step": "",
    }

    if not question:
        empty_result["answer"] = "Please enter a question."
        empty_result["next_step"] = "Enter a question and try again."
        return empty_result

    if not isinstance(followups, pd.DataFrame):
        followups = pd.DataFrame()

    records = followups.copy()

    if records.empty:
        return {
            "answer": "No follow-up records are available to analyse.",
            "records": records,
            "next_step": "Check the source registers and reload the data.",
        }

    status = records.get(
        "Finding Status", pd.Series("", index=records.index)
    ).fillna("").astype(str)

    priority = records.get(
        "Priority", pd.Series("", index=records.index)
    ).fillna("").astype(str)

    # Identify the type of question and apply explicit rules.
    if any(term in question for term in [
        "work order", "work-order", "wo preparation",
        "wo number", "wo no",
    ]):
        order_records = records[
            status.eq("Order received — WO check")
        ]

        if any(term in question for term in [
            "still need", "blank", "missing", "pending",
            "check", "without",
        ]):
            records = order_records
            answer = (
                f"Found {len(records)} recorded order(s) requiring "
                "a work-order preparation check."
            )
            next_step = (
                "Confirm work-order preparation status with the "
                "responsible team."
            )
        else:
            records = records[
                status.isin([
                    "Order received — WO check",
                    "Order recorded",
                ])
            ]
            answer = (
                f"Found {len(records)} record(s) marked as orders "
                "received. Review the work-order status in each row."
            )
            next_step = (
                "Verify the work-order reference and handoff status "
                "for each order."
            )

    elif any(term in question for term in [
        "attention", "priority", "urgent", "review",
        "follow up", "follow-up",
    ]):
        records = records[
            priority.isin(["Urgent", "High", "Needs review"])
        ]
        answer = (
            f"Found {len(records)} record(s) marked Urgent, High, "
            "or Needs review."
        )
        next_step = (
            "Review the finding and recommended action for each "
            "record. Confirm ownership and timing with the team."
        )

    elif any(term in question for term in [
        "blocker", "blockers", "problem", "problems",
        "unresolved", "issue", "issues",
    ]):
        finding_text = records.get(
            "Blocker / Finding",
            pd.Series("", index=records.index),
        ).fillna("").astype(str)

        records = records[
            finding_text.str.strip().ne("")
        ]
        answer = (
            f"Found {len(records)} record(s) with a documented "
            "finding or potential blocker. These findings may "
            "require verification."
        )
        next_step = (
            "Review each finding and confirm the facts with the "
            "responsible team before taking action."
        )

    elif any(term in question for term in [
        "pipeline", "summarize", "summary", "overall",
        "how many", "total",
    ]):
        answer = (
            f"Pipeline summary: {metrics.get('total_enquiries', 0)} "
            f"enquiries, {metrics.get('quotations_issued', 0)} "
            f"quotations, {metrics.get('orders_received', 0)} "
            f"recorded orders, and {metrics.get('wo_check', 0)} "
            "orders requiring a work-order check."
        )
        next_step = (
            "Review records requiring a work-order check and "
            "items marked Needs review."
        )

    else:
        # Attempt a simple client, item, or reference search.
        searchable_columns = [
            "Client Name",
            "Item",
            "Enquiry Reference",
            "WO No.",
        ]
        available_columns = [
            col for col in searchable_columns if col in records.columns
        ]

        terms = [
            word.strip(".,?!:;()[]{}\"'")
            for word in question.split()
            if len(word.strip(".,?!:;()[]{}\"'")) >= 3
        ]

        if available_columns and terms:
            searchable = records[available_columns].fillna("").astype(str)
            row_text = searchable.agg(" ".join, axis=1).str.lower()
            mask = row_text.apply(
                lambda value: any(term in value for term in terms)
            )
            records = records[mask]

            answer = (
                f"Found {len(records)} record(s) matching your "
                "search terms. A text match does not prove an "
                "order outcome or a missed follow-up."
            )
            next_step = (
                "Inspect the matching records and verify their "
                "status against the source registers."
            )
        else:
            records = pd.DataFrame()
            answer = (
                "I could not determine a specific analysis from "
                "that question using the available rule-based "
                "functions."
            )
            next_step = (
                "Try asking about records needing attention, "
                "orders requiring a work-order check, blockers, "
                "or the current pipeline."
            )

    return {
        "answer": answer,
        "records": records.reset_index(drop=True),
        "next_step": next_step,
    }


def explain_with_openai(
    question: str,
    base_result: Any,
    metrics: Any,
) -> str:
    """Optionally explain Python findings using OpenAI."""

    api_key = _get_setting("OPENAI_API_KEY")

    if not api_key:
        return (
            "AI explanation is disabled because OPENAI_API_KEY "
            "is not configured. Python findings remain available."
        )

    try:
        import json
        from openai import OpenAI

        if not isinstance(base_result, dict):
            return "AI explanation unavailable: invalid findings format."

        # Send only the summary, not complete enquiry or quotation registers.
        records = base_result.get("records", pd.DataFrame())
        record_count = (
            len(records) if isinstance(records, pd.DataFrame) else 0
        )

        payload = {
            "question": question,
            "python_answer": str(base_result.get("answer", "")),
            "next_step": str(base_result.get("next_step", "")),
            "matching_record_count": record_count,
            "metrics": _safe_metrics(metrics),
        }

        client = OpenAI(
            api_key=api_key,
            timeout=20.0,
            max_retries=1,
        )
        response = client.responses.create(
            model=_get_setting("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=(
                "Explain the supplied Python findings clearly and "
                "concisely. Do not invent counts, dates, clients, or "
                "business outcomes. A blank work-order number does "
                "not prove an order was lost. State uncertainty when "
                "the evidence is insufficient."
            ),
            input=json.dumps(payload, ensure_ascii=False),
        )

        explanation = (response.output_text or "").strip()
        return explanation or "The AI service returned no explanation."

       except Exception as exc:
        return (
            f"AI explanation failed: {type(exc).__name__}: {exc}\n\n"
            "Python findings remain available. Check your API key, "
            "model access, account billing, and Streamlit logs."
        )


def _get_setting(name: str, default: str = "") -> str:
    """Read Streamlit Secrets first, then environment variables."""

    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _safe_metrics(metrics: Any) -> dict:
    """Keep simple metric values only."""

    if not isinstance(metrics, dict):
        return {}

    return {
        str(key): value
        for key, value in metrics.items()
        if isinstance(value, (str, int, float, bool))
        or value is None
    }
