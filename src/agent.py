import pandas as pd

def answer_demo_question(question, enquiries, quotations, followups, metrics):
    q = question.lower()
    if any(term in q for term in ["work order", "work-order", "wo"]):
        records = followups[followups["Finding Status"] == "Order received — WO check"].copy()
        answer = f"{len(records)} synthetic quotation record(s) show an order received with no work-order number recorded."
        next_step = "Ask the responsible team to verify work-order preparation. A blank number is a prompt to check, not proof that work has not started."
    elif any(term in q for term in ["blocker", "pending", "issue"]):
        records = followups[followups["Priority"].isin(["Urgent", "High", "Needs review"])].copy()
        answer = f"{len(records)} record(s) are marked High or Needs review. Review the finding and source register before assigning actions."
        next_step = "Confirm ownership and the latest customer/team update; then record a real next-action date in your operational process."
    elif any(term in q for term in ["attention", "priority", "urgent", "follow"]):
        records = followups[followups["Priority"].isin(["Urgent", "High", "Needs review"])].copy()
        answer = f"{len(records)} record(s) are currently flagged for attention in this synthetic dataset."
        next_step = "Start with High-priority records, then resolve ambiguous records. This demo does not invent due dates."
    elif any(term in q for term in ["pipeline", "summary", "summarize", "overview"]):
        records = followups.copy()
        answer = (f"The synthetic register contains {metrics['total_enquiries']} enquiries and {metrics['quotations_issued']} quotations. "
                  f"{metrics['orders_received']} quotations record a customer order; {metrics['wo_check']} of those have no work-order number recorded.")
        next_step = "Verify the source registers and confirm that the sample records reflect the intended business definitions."
    else:
        records = pd.DataFrame()
        answer = "I could not map that question to a supported demo query. Try asking about attention items, work-order checks, blockers, or the pipeline."
        next_step = "Use one of the example questions or narrow the request to a known register field."
    return {"answer": answer, "records": records, "next_step": next_step}

import streamlit as st
from openai import OpenAI


def explain_with_openai(question, base_result, metrics):
    api_key = st.secrets.get("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OpenAI API key is missing. Configure it in Streamlit Secrets."
        )

    model = st.secrets.get("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)

    # Send only the rule-based findings needed to answer the question.
    context = {
        "metrics": metrics,
        "findings": base_result["answer"],
        "next_step": base_result["next_step"],
        "records": base_result["records"]
            .head(12)
            .fillna("")
            .to_dict(orient="records"),
    }

    response = client.responses.create(
        model=model,
        instructions=(
            "You are an enquiry monitoring assistant for a boiler "
            "manufacturing business. Answer using only the supplied "
            "context. Do not invent clients, statuses, dates, values, "
            "or counts. Distinguish known facts from unknown information. "
            "Treat the Python findings and metrics as authoritative. "
            "Give a concise explanation and practical next step. "
            "All supplied records are synthetic demo data."
        ),
        input=(
            f"User question: {question}\n\n"
            f"Verified Python context: {context}"
        ),
        max_output_tokens=350,
    )

    return response.output_text
