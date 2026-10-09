
"""Question-answering and optional AI explanation for the enquiry dashboard."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd


def _normalise(value: Any) -> str:
    """Convert a value to searchable, lowercase text."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _safe_metrics(metrics: Any) -> dict:
    """Keep only simple, serialisable metric values."""
    if not isinstance(metrics, dict):
        return {}

    safe = {}

    for key, value in metrics.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value
        elif isinstance(value, dict):
            safe[str(key)] = {
                str(k): v
                for k, v in value.items()
                if isinstance(v, (str, int, float, bool))
                or v is None
            }

    return safe


def _find_matching_rows(
    question: str,
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
) -> list[str]:
    """Find basic text matches without guessing business status."""
    terms = [
        term.strip(".,?!:;()[]{}\"'")
        for term in question.lower().split()
    ]
    terms = [term for term in terms if len(term) >= 3]

    if not terms:
        return []

    findings = []

    for label, frame in (
        ("Enquiry Register", enquiries),
        ("Quotation Register", quotations),
    ):
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue

        searchable = frame.fillna("").astype(str)
        row_text = searchable.apply(
            lambda row: " ".join(row.values).lower(), axis=1
        )

        # Require a term to match a row; cap displayed results.
        mask = row_text.apply(
            lambda value: any(term in value for term in terms)
        )
        matches = frame.loc[mask]

        if matches.empty:
            continue

        findings.append(
            f"{label}: {len(matches)} matching row(s) found."
        )

        # Display a few useful fields, not the entire register.
        preferred = [
            "Client Name",
            "Item",
            "Items",
            "Enq. No. & Date",
            "Quotation No.",
            "WO No.",
            "Remark",
        ]
        available = [
            col for col in preferred if col in matches.columns
        ]

        for _, row in matches.head(5).iterrows():
            details = [
                f"{col}: {str(row[col])}"
                for col in available
                if str(row[col]).strip()
                and str(row[col]).lower() != "nan"
            ]
            if details:
                findings.append(" - " + "; ".join(details))

    return findings


def answer_demo_question(
    question: str,
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
    followups: pd.DataFrame,
    metrics: dict,
) -> dict:
    """
    Produce transparent Python findings for the dashboard.

    Blank fields are treated as unknown, not proof of a lost order
    or a missed follow-up.
    """
    question = (question or "").strip()

    if not question:
        return {
            "answer": "Enter a question to analyse the available data.",
            "findings": [],
        }

    findings = []

    if isinstance(enquiries, pd.DataFrame):
        findings.append(
            f"Enquiry Register contains {len(enquiries)} row(s)."
        )
    else:
        enquiries = pd.DataFrame()
        findings.append("Enquiry Register is unavailable.")

    if isinstance(quotations, pd.DataFrame):
        findings.append(
            f"Quotation Register contains {len(quotations)} row(s)."
        )
    else:
        quotations = pd.DataFrame()
        findings.append("Quotation Register is unavailable.")

    if isinstance(followups, pd.DataFrame):
        findings.append(
            f"Follow-up view contains {len(followups)} row(s)."
        )
    else:
        followups = pd.DataFrame()

    safe_metrics = _safe_metrics(metrics)
    if safe_metrics:
        findings.append(
            "Available summary metrics: "
            + json.dumps(safe_metrics, ensure_ascii=False)
        )

    matching = _find_matching_rows(
        question, enquiries, quotations
    )
    findings.extend(matching)

    if matching:
        answer = (
            "I found rows matching some of the words in your question. "
            "Review the matching records below; keyword matches alone "
            "do not establish order status, loss of business, or "
            "whether a follow-up is overdue."
        )
    else:
        answer = (
            "The available data has been summarised, but I could not "
            "identify a reliable record-level answer from a basic "
            "keyword search. Check the register fields and summary "
            "metrics before drawing a business conclusion."
        )

    return {
        "answer": answer,
        "findings": findings,
        "metrics": safe_metrics,
    }


def _get_setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit Secrets or environment variables."""
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        # Secrets may not exist outside a configured Streamlit app.
        pass

    return os.getenv(name, default)


def explain_with_openai(
    question: str,
    base_result: Any,
    metrics: Any,
) -> str:
    """Explain existing Python findings using the configured OpenAI API."""
    api_key = _get_setting("OPENAI_API_KEY")

    if not api_key:
        return (
            "AI explanation is disabled because OPENAI_API_KEY is not "
            "configured. The Python findings remain available above."
        )

    if isinstance(base_result, dict):
        python_findings = {
            "answer": base_result.get("answer", ""),
            "findings": base_result.get("findings", []),
            "metrics": _safe_metrics(base_result.get("metrics", {})),
        }
    else:
        python_findings = {"answer": str(base_result)}

    payload = {
        "question": question,
        "python_findings": python_findings,
        "summary_metrics": _safe_metrics(metrics),
    }

    try:
        from openai import OpenAI

        model = _get_setting("OPENAI_MODEL", "gpt-4.1-mini")
        client = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)

        response = client.responses.create(
            model=model,
            instructions=(
                "You explain enquiry and quotation analysis for a "
                "business dashboard. Use only the supplied findings. "
                "Do not invent counts, dates, clients, or status. "
                "Distinguish missing information from negative outcomes. "
                "A blank work order number does not prove that an order "
                "was lost or that work-order preparation is overdue. "
                "If evidence is insufficient, say so. Be concise."
            ),
            input=json.dumps(payload, ensure_ascii=False, default=str),
        )

        explanation = (response.output_text or "").strip()

        if not explanation:
            return "The AI service returned an empty explanation."

        return explanation

    except ImportError:
        return (
            "AI explanation unavailable: install the 'openai' package "
            "using requirements.txt. Python findings are still available."
        )
    except Exception:
        return (
            "AI explanation is temporarily unavailable. Check the "
            "Streamlit app logs and API configuration. Python findings "
            "are still available above."
        )
