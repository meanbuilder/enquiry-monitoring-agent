import pandas as pd

def _norm(value):
    return str(value or "").strip().lower()

def build_followup_view(enquiries: pd.DataFrame, quotations: pd.DataFrame) -> pd.DataFrame:
    """Build a transparent, rule-based action view from synthetic register rows."""
    rows = []
    for _, q in quotations.iterrows():
        remark = _norm(q.get("Remark", ""))
        wo_no = str(q.get("WO No.", "")).strip()
        order_received = "order rec" in remark or "order received" in remark
        if order_received and not wo_no:
            status, priority = "Order received — WO check", "High"
            finding = "Customer order is recorded, but the work-order number is blank."
            action = "Confirm work-order preparation status with the responsible team."
        elif order_received and wo_no:
            status, priority = "Order recorded", "Normal"
            finding = "Customer order and work-order reference are both recorded."
            action = "Verify handoff and delivery milestones in the source system."
        elif not remark and not wo_no:
            status, priority = "Unknown — review", "Needs review"
            finding = "Remark and work-order number are blank; outcome cannot be inferred."
            action = "Check the latest customer communication and update the register."
        else:
            status, priority = "Quotation follow-up", "Normal"
            finding = "No confirmed order outcome is recorded in the available fields."
            action = "Review the latest follow-up and decide whether another contact is due."
        rows.append({"Client Name": q.get("Client Name", ""), "Enquiry Reference": q.get("Quotation No.", ""), "Item": q.get("Items", ""), "Quotation Date": q.get("Quotation Date", ""), "Quotation Value": q.get("Total Value", ""), "Finding Status": status, "Priority": priority, "Blocker / Finding": finding, "Recommended Next Action": action, "WO No.": wo_no, "Source": "Quotation Register"})

    quote_clients = {_norm(x) for x in quotations.get("Client Name", pd.Series(dtype=str)).tolist()}
    for _, e in enquiries.iterrows():
        client = e.get("Client Name", "")
        if _norm(client) not in quote_clients:
            review = str(e.get("ENQ Review", "")).strip()
            if review:
                finding = f"Enquiry review note: {review}"
                action = "Confirm the owner, latest status and next action with the marketing team."
                priority = "High" if any(k in _norm(review) for k in ["pending", "await", "required", "drawing"]) else "Needs review"
            else:
                finding = "No linked quotation was found by exact client-name match; this may be a data-linkage issue."
                action = "Verify whether a quotation exists under a different client name or reference."
                priority = "Needs review"
            rows.append({"Client Name": client, "Enquiry Reference": e.get("Enq. No. & Date", ""), "Item": e.get("Item", ""), "Quotation Date": "", "Quotation Value": "", "Finding Status": "Enquiry needs review", "Priority": priority, "Blocker / Finding": finding, "Recommended Next Action": action, "WO No.": "", "Source": "Enquiry Register"})
    columns = ["Client Name", "Enquiry Reference", "Item", "Quotation Date", "Quotation Value", "Finding Status", "Priority", "Blocker / Finding", "Recommended Next Action", "WO No.", "Source"]
    result = pd.DataFrame(rows, columns=columns)
    if not result.empty:
        order = {"Urgent": 0, "High": 1, "Needs review": 2, "Normal": 3}
        result = result.sort_values(by="Priority", key=lambda s: s.map(order).fillna(4), kind="stable").reset_index(drop=True)
    return result

def summarize_metrics(enquiries, quotations, followups):
    remarks = quotations.get("Remark", pd.Series(dtype=str)).astype(str).str.lower()
    wo = quotations.get("WO No.", pd.Series(dtype=str)).astype(str).str.strip()
    orders = remarks.str.contains("order rec|order received", regex=True, na=False)
    return {"total_enquiries": int(len(enquiries)), "quotations_issued": int(len(quotations)), "orders_received": int(orders.sum()), "wo_check": int((orders & wo.eq("")).sum()), "needs_review": int((followups["Priority"] == "Needs review").sum()) if not followups.empty else 0}
