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
    """
    Recognise known order-confirmation wording, including
    the demo spelling 'Order Reced'.

    Deliberately avoids treating every occurrence of 'order'
    as confirmation.
    """
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
    """
    Build one row per quotation and append relevant enquiry
    information when a client/item match is available.

    A missing enquiry match does not discard a quotation.
    A missing work order does not mean an order was lost.
    """
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

    def priority(row):
        if row["Order Confirmed"] and not row["Work Order Recorded"]:
            return "High"
        return "Normal"

    result["Follow-up Priority"] = result.apply(priority, axis=1)
    result["Priority"] = result["Follow-up Priority"]

    # Match by client name and item where possible.
    # Keep all quotation rows even if no enquiry matches.
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

    return result


def summarize_metrics(
    enquiries: pd.DataFrame,
    quotations: pd.DataFrame,
) -> dict:
    """Calculate dashboard metrics using Python, not the AI model."""
    followups = build_followup_view(enquiries, quotations)

    values = pd.to_numeric(
        quotations["Total Value"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0)

    confirmed = followups["Order Confirmed"]
    with_wo = followups["Work Order Recorded"]

    return {
        "total_enquiries": int(len(enquiries)),
        "total_quotations": int(len(quotations)),
        "total_quotation_value": float(values.sum()),
        "orders_confirmed": int(confirmed.sum()),
        "work_orders_recorded": int((confirmed & with_wo).sum()),
        "confirmed_orders_missing_wo": int((confirmed & ~with_wo).sum()),
        "followups_required": int(
            (followups["Follow-up Status"] == "Follow-up required").sum()
        ),
        "awaiting_status_update": int(
            (followups["Follow-up Status"] == "Awaiting status update").sum()
        ),
    }
