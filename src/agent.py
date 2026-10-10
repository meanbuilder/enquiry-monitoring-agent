"""Gemini-powered EnquiryPulse agent with allowlisted tools."""

import json
import os
import re

import pandas as pd

from src.ai_tools import ALLOWED_TOOLS, execute_tool


def _setting(name: str, default: str = "") -> str:
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _get_client():
    api_key = _setting("GEMINI_API_KEY")

    if not api_key:
        return None

    from google import genai

    return genai.Client(api_key=api_key)


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _fallback_route(question: str) -> tuple[str, dict]:
    """Simple deterministic fallback when Gemini is unavailable."""

    q = question.casefold()

    if any(word in q for word in ["draft", "email", "follow-up email"]):
        match = re.search(
            r"(?:for|to)\s+(.+)$",
            question,
            flags=re.IGNORECASE,
        )
        client = match.group(1).strip() if match else ""
        return "draft_followup", {"client_name": client}

    if "decision brief" in q or "decision for ceo" in q:
        return "decision_brief", {"question": question}

    if any(
        word in q
        for word in ["urgent", "high priority", "attention", "blocker", "stalled"]
    ):
        return "priority_records", {"priority": "High"}

    if any(
        word in q for word in ["pipeline", "summary", "how many", "overall", "total"]
    ):
        return "pipeline_summary", {}

    query = re.sub(
        r"^(find|search|show|which|who|what about)\s+",
        "",
        question,
        flags=re.IGNORECASE,
    ).strip(" ?.")

    return "search_records", {"query": query or question}


def _route_with_gemini(client, question: str) -> dict:
    prompt = f"""
You route questions for an industrial sales-enquiry assistant.

Choose exactly ONE approved tool:
1. pipeline_summary — arguments: {{}}
2. priority_records — arguments: {{"priority":"High"}}
3. search_records — arguments: {{"query":"search term"}}
4. draft_followup — arguments: {{"client_name":"client name"}}
5. decision_brief — arguments: {{"question":"management question"}}

Return JSON only:
{{"tool":"approved_tool_name","args":{{}}}}

Do not answer the business question.
Do not invent client names.
Never select tools outside the allowlist.
If a draft is requested but the client is unclear, use an empty client_name.

Question: {question}
"""

    response = client.models.generate_content(
        model=_setting("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    route = _parse_json(getattr(response, "text", ""))

    if route.get("tool") not in ALLOWED_TOOLS:
        return {}

    args = route.get("args", {})
    return {
        "tool": route["tool"],
        "args": args if isinstance(args, dict) else {},
    }


def _explain_with_gemini(client, question, result, metrics) -> str:
    records = result.get("records")
    record_data = []

    if isinstance(records, pd.DataFrame) and not records.empty:
        allowed_columns = [
            "Client Name",
            "Enquiry Reference",
            "Item",
            "Finding Status",
            "Priority",
            "Blocker / Finding",
            "Recommended Next Action",
            "WO No.",
            "Source",
        ]

        columns = [column for column in allowed_columns if column in records.columns]

        record_data = records[columns].head(12).fillna("").to_dict(orient="records")

    evidence = {
        "question": question,
        "python_result": result.get("answer", ""),
        "next_step": result.get("next_step", ""),
        "evidence": result.get("evidence", {}),
        "records": record_data,
        "metrics": metrics,
        "action_kind": result.get("action_kind", ""),
    }

    instructions = """
You are EnquiryPulse, a careful industrial sales-operations assistant.

Explain only the supplied evidence. Never invent counts, dates, client details,
causes, order outcomes, prices, or delivery commitments.

Distinguish recorded facts from hypotheses. A blank remark or work-order number
does not prove an order was lost.

For a follow-up request, draft a professional email with subject and body.
Never claim an email was sent.

For a decision brief, state the recommendation, supported options, risks or
unknowns, and one proposed internal next step.

Keep the response concise and practical.
"""

    response = client.models.generate_content(
        model=_setting("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=(
            instructions
            + "\n\nEvidence JSON:\n"
            + json.dumps(evidence, ensure_ascii=False, default=str)
        ),
    )

    return (getattr(response, "text", "") or "").strip()


def answer_question(
    question: str,
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
    followups: pd.DataFrame,
    metrics: dict,
) -> dict:
    question = (question or "").strip()

    if not question:
        return {
            "answer": "Please enter a question.",
            "records": followups.head(0).copy(),
            "next_step": "Enter a question and try again.",
            "tool": "",
        }

    client = None
    try:
        client = _get_client()
    except Exception:
        pass

    route = {}

    if client is not None:
        try:
            route = _route_with_gemini(client, question)
        except Exception:
            route = {}

    if route:
        tool_name = route["tool"]
        args = route["args"]
    else:
        tool_name, args = _fallback_route(question)

    result = execute_tool(
        tool_name,
        args,
        enquiries,
        quotations,
        followups,
        metrics,
    )

    result["tool"] = tool_name

    if tool_name == "draft_followup":
        records = result.get("records")

        if records is None or records.empty:
            result["answer"] = (
                "No matching client record was found. "
                "No customer-specific draft was generated."
            )
            result["draft"] = ""
        else:
            result["action_kind"] = "draft"

    if client is not None:
        try:
            result["ai_summary"] = _explain_with_gemini(
                client, question, result, metrics
            )
        except Exception:
            result["ai_summary"] = (
                "Gemini could not generate an explanation. "
                "Review the Python findings and source records."
            )
    else:
        result["ai_summary"] = (
            "Gemini is not configured. The Python analysis ran, but no "
            "AI-generated explanation was produced. Configure GEMINI_API_KEY "
            "in Streamlit Secrets."
        )

    return result
