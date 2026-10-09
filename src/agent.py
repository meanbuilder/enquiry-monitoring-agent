
"""Rule-based enquiry analysis with optional OpenAI explanations."""

from __future__ import annotations

import json
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
    """Analyse follow-up records using explicit Python rules."""

    question = (question or "").strip().lower()

    if not question:
        return {
            "answer": "Please enter a question.",
            "records": pd.DataFrame(),
            "next_step": "Enter a question and try again.",
        }

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
        "Finding Status",
        pd.Series("", index=records.index),
    ).fillna("").astype(str)

    priority = records.get(
        "Priority",
        pd.Series("", index=records.index),
    ).fillna("").astype(str)

    # Work-order questions
    if any(term in question for term in [
        "work order",
        "work-order",
        "wo preparation",
        "wo number",
        "wo no",
    ]):
        if any(term in question for term in [
            "still need",
            "blank",
            "missing",
            "pending",
            "check",
            "without",
        ]):
            records = records[
                status.eq("Order received — WO check")
            ]

            answer = (
                f"Found {len(records)} recorded order(s) "
                "requiring a work-order preparation check."
            )
            next_step = (
                "Confirm work-order preparation status with "
                "the responsible team."
            )
        else:
            records = records[
                status.isin([
                    "Order received — WO check",
                    "Order recorded",
                ])
            ]

            answer = (
                f"Found {len(records)} record(s) marked as "
                "orders received. Review the work-order status "
                "in each record."
            )
            next_step = (
                "Verify the work-order reference and handoff "
                "status for each order."
            )

    # Priority and attention questions
    elif any(term in question for term in [
        "attention",
        "priority",
        "urgent",
        "review",
        "follow up",
        "follow-up",
    ]):
        records = records[
            priority.isin(["Urgent", "High", "Needs review"])
        ]

        answer = (
            f"Found {len(records)} record(s) marked Urgent, "
            "High, or Needs review."
        )
        next_step = (
            "Review each finding and recommended action. "
            "Confirm ownership and timing with the team."
        )

    # Blocker questions
    elif any(term in question for term in [
        "blocker",
        "blockers",
        "problem",
        "problems",
        "unresolved",
        "issue",
        "issues",
    ]):
        finding_text = records.get(
            "Blocker / Finding",
            pd.Series("", index=records.index),
        ).fillna("").astype(str)

        records = records[finding_text.str.strip().ne("")]

        answer = (
            f"Found {len(records)} record(s) with a documented "
            "finding or potential blocker. Verification may "
            "be required."
        )
        next_step = (
            "Review each finding and confirm the facts with "
            "the responsible team before taking action."
        )

    # Pipeline summary questions
    elif any(term in question for term in [
        "pipeline",
        "summarize",
        "summary",
        "overall",
        "how many",
        "total",
    ]):
        metrics = metrics if isinstance(metrics, dict) else {}

        answer = (
            f"Pipeline summary: "
            f"{metrics.get('total_enquiries', 0)} enquiries, "
            f"{metrics.get('quotations_issued', 0)} quotations, "
            f"{metrics.get('orders_received', 0)} recorded orders, "
            f"and {metrics.get('wo_check', 0)} orders requiring "
            "a work-order check."
        )
        next_step = (
            "Review records requiring a work-order check and "
            "items marked Needs review."
        )

    # Basic record search
    else:
        searchable_columns = [
            "Client Name",
            "Item",
            "Enquiry Reference",
            "WO No.",
        ]

        available_columns = [
            column
            for column in searchable_columns
            if column in records.columns
        ]

        terms = [
            word.strip(".,?!:;()[]{}\"'")
            for word in question.split()
            if len(word.strip(".,?!:;()[]{}\"'")) >= 3
        ]

        if available_columns and terms:
            searchable = (
                records[available_columns]
                .fillna("")
                .astype(str)
            )

            row_text = searchable.agg(" ".join, axis=1).str.lower()

            mask = row_text.apply(
                lambda value: any(
                    term in value for term in terms
                )
            )

            records = records[mask]

            answer = (
                f"Found {len(records)} record(s) matching "
                "your search terms. A text match alone does "
                "not establish an order outcome."
            )
            next_step = (
                "Inspect the matching records and verify "
                "their status against the source registers."
            )
        else:
            records = pd.DataFrame()

            answer = (
                "I could not determine a specific answer using "
                "the available rule-based analysis."
            )
            next_step = (
                "Try asking about records needing attention, "
                "work-order checks, blockers, or the pipeline."
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
    """Explain Python findings using the OpenAI API."""

    api_key = _get_setting("OPENAI_API_KEY")

    if not api_key:
        return (
            "AI explanation unavailable: OPENAI_API_KEY is not "
            "configured in Streamlit Secrets. Python findings "
            "remain available."
        )

    if not isinstance(base_result, dict):
        return "AI explanation unavailable: invalid findings format."

    try:
        from openai import OpenAI

        result_records = base_result.get("records")

        # Share only a limited selection of relevant fields and rows.
        safe_records = []

        if (
            isinstance(result_records, pd.DataFrame)
            and not result_records.empty
        ):
            allowed_columns = [
                "Client Name",
                "Item",
                "Enquiry Reference",
                "Finding Status",
                "Priority",
                "Blocker / Finding",
                "Recommended Next Action",
                "WO No.",
            ]

            columns = [
                column
                for column in allowed_columns
                if column in result_records.columns
            ]

            safe_records = (
                result_records[columns]
                .head(10)
                .fillna("")
                .to_dict(orient="records")
            )

        payload = {
            "question": question,
            "python_answer": str(base_result.get("answer", "")),
            "recommended_next_step": str(
                base_result.get("next_step", "")
            ),
            "matching_records": safe_records,
            "summary_metrics": _safe_metrics(metrics),
        }

        client = OpenAI(
            api_key=api_key,
            timeout=30.0,
            max_retries=1,
        )

        response = client.responses.create(
            model=_get_setting(
                "OPENAI_MODEL",
                "gpt-4.1-mini",
            ),
            instructions=(
                "You are an enquiry monitoring business assistant. "
                "Explain the supplied Python findings in concise, "
                "professional language suitable for management. "
                "Use the supplied records and metrics only. Do not "
                "invent counts, dates, clients, or business outcomes. "
                "Do not claim a quotation is lost unless the evidence "
                "explicitly establishes that. A blank work-order "
                "number means its status needs checking; it does not "
                "prove the order was lost or the work order is overdue. "
                "Distinguish facts from recommendations. If evidence "
                "is insufficient, say so. Suggest practical next steps "
                "but do not claim to have contacted anyone or changed "
                "any records."
            ),
            input=json.dumps(payload, ensure_ascii=False, default=str),
        )

        explanation = (response.output_text or "").strip()

        if not explanation:
            return "AI explanation unavailable: the API returned an empty response."

        return explanation

    except Exception as exc:
        # Diagnostic message excludes the API key.
        return (
            f"AI explanation failed: {type(exc).__name__}: {exc}\n\n"
            "Python findings remain available. Check the model "
            "setting, API access, account usage limits, and "
            "Streamlit Cloud logs."
        )


def _get_setting(name: str, default: str = "") -> str:
    """Read Streamlit Secrets, then environment variables."""

    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _safe_metrics(metrics: Any) -> dict:
    """Return simple values suitable for the AI request."""

    if not isinstance(metrics, dict):
        return {}

    safe = {}

    for key, value in metrics.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value

    return safe
