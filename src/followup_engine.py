import re

import pandas as pd

ORDER_PHRASES = (
    "order received",
    "order rec",
    "order recd",
    "order receiv",
    "po received",
    "purchase order received",
)


def _clean(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalise(value) -> str:
    value = _clean(value).casefold()
    return re.sub(r"\s+", " ", value)


def _is_order_received(remark: str) -> bool:
    text = _normalise(remark)
    if not text:
        return False
    return any(phrase in text for phrase in ORDER_PHRASES)


def _has_work_order(value: str) -> bool:
    return bool(_clean(value))


def build_followup_view(
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
) -> pd.DataFrame:
    """Build quotation follow-ups and attach matching enquiry details."""

    result = quotations.copy()

    result["Order Confirmed"] = result["Remark"].apply(_is_order_received)
    result["Work Order Recorded"] = result["WO No."].apply(_has_work_order)

    def classify(row):
        if row["Order Confirmed"] and not row["Work Order Recorded"]:
            return "Order confirmed — WO missing"

        if row["Order Confirmed"] and row["Work Order Recorded"]:
            return "Order confirmed — WO recorded"

        if not _clean(row.get("Remark", "")):
            return "Awaiting status update"

        return "Follow-up required"

    result["Follow-up Status"] = result.apply(classify, axis=1)

    result["Finding Status"] = result["Follow-up Status"]

    def priority(row):
        if row["Order Confirmed"] and not row["Work Order Recorded"]:
            return "High"
        return "Normal"

    result["Follow-up Priority"] = result.apply(priority, axis=1)
    result["Priority"] = result["Follow-up Priority"]

    # Match enquiries to quotations by client and item.
    enquiry_lookup = enquiries.copy()

    enquiry_lookup["_client_key"] = enquiry_lookup["Client Name"].map(_normalise)
    enquiry_lookup["_item_key"] = enquiry_lookup["Item"].map(_normalise)

    result["_client_key"] = result["Client Name"].map(_normalise)
    result["_item_key"] = result["Items"].map(_normalise)

    enquiry_columns = [
        column
        for column in [
            "Enq. No. & Date",
            "Enq. Rec. Date",
            "Due Date",
            "ENQ Review",
            "Quotaion Priority",
            "Quotation Evaluation status",
            "Remarks",
        ]
        if column in enquiry_lookup.columns
    ]

    enquiry_lookup = enquiry_lookup[
        ["_client_key", "_item_key"] + enquiry_columns
    ].drop_duplicates(
        subset=["_client_key", "_item_key"],
        keep="first",
    )

    result = result.merge(
        enquiry_lookup,
        on=["_client_key", "_item_key"],
        how="left",
        suffixes=("", "_Enquiry"),
    )

    result.drop(
        columns=["_client_key", "_item_key"],
        inplace=True,
        errors="ignore",
    )

    # Dashboard compatibility columns.
    if "Enq. No. & Date" in result.columns:
        result["Enquiry Reference"] = result["Enq. No. & Date"].fillna("")
    else:
        result["Enquiry Reference"] = ""

    result["Item"] = result["Items"].fillna("")

    def blocker(row):
        if row["Order Confirmed"] and not row["Work Order Recorded"]:
            return "Order confirmed but work order missing"

        if row["Follow-up Status"] == "Awaiting status update":
            return "Quotation status needs update"

        if row["Follow-up Status"] == "Follow-up required":
            return "Follow-up required"

        return ""

    result["Blocker / Finding"] = result.apply(blocker, axis=1)

    def next_action(row):
        if row["Order Confirmed"] and not row["Work Order Recorded"]:
            return "Confirm and record the work order number"

        if row["Follow-up Status"] in (
            "Awaiting status update",
            "Follow-up required",
        ):
            return "Contact the customer for a status update"

        if row["Work Order Recorded"]:
            return "Verify the recorded work order"

        return ""

    result["Recommended Next Action"] = result.apply(next_action, axis=1)

    return result


def summarize_metrics(
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
) -> dict:
    """Calculate dashboard metrics using Python."""

    followups = build_followup_view(enquiries, quotations)

    values = pd.to_numeric(
        quotations["Total Value"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0)

    confirmed = followups["Order Confirmed"]
    with_wo = followups["Work Order Recorded"]

    followup_required = followups["Follow-up Status"] == "Follow-up required"
    awaiting_update = followups["Follow-up Status"] == "Awaiting status update"
    confirmed_missing_wo = confirmed & ~with_wo

    return {
        "total_enquiries": int(len(enquiries)),
        "total_quotations": int(len(quotations)),
        "quotations_issued": int(len(quotations)),
        "total_quotation_value": float(values.sum()),
        "orders_confirmed": int(confirmed.sum()),
        "orders_received": int(confirmed.sum()),
        "work_orders_recorded": int((confirmed & with_wo).sum()),
        "wo_check": int((confirmed & with_wo).sum()),
        "confirmed_orders_missing_wo": int(confirmed_missing_wo.sum()),
        "followups_required": int(followup_required.sum()),
        "needs_review": int(followup_required.sum() + confirmed_missing_wo.sum()),
        "awaiting_status_update": int(awaiting_update.sum()),
    }
