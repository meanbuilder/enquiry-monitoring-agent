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
