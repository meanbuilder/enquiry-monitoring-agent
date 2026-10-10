import pandas as pd
from src.followup_engine import (
    _is_order_received,
    build_followup_view,
    summarize_metrics,
)


def test_order_spelling_variants():
    assert _is_order_received("Order Reced")
    assert _is_order_received("Order Received")
    assert _is_order_received("Order Recd")
    assert not _is_order_received("Under customer review")
    assert not _is_order_received("Rate clarification awaited")


def test_order_without_work_order_is_flagged():
    enquiries = pd.DataFrame(columns=["Client Name", "Enq. No. & Date", "Item"])
    quotations = pd.DataFrame(
        [
            {
                "Quotation No.": "Q1",
                "Client Name": "Northstar Process Systems",
                "Items": "Inbed Coils",
                "Remark": "Order Reced",
                "WO No.": "",
                "Total Value": "425000",
            }
        ]
    )

    result = build_followup_view(enquiries, quotations)

    assert result.loc[0, "Order Confirmed"]
    assert not result.loc[0, "Work Order Recorded"]
    assert result.loc[0, "Follow-up Priority"] == "High"
    assert result.loc[0, "Follow-up Status"] == "Order confirmed — WO missing"


def test_order_with_work_order_is_recorded():
    enquiries = pd.DataFrame(columns=["Client Name", "Enq. No. & Date", "Item"])
    quotations = pd.DataFrame(
        [
            {
                "Quotation No.": "Q2",
                "Client Name": "Meridian Energy Works",
                "Items": "Water Wall Assembly",
                "Remark": "Order Reced",
                "WO No.": "DEMO-WO-3001",
                "Total Value": "910000",
            }
        ]
    )

    result = build_followup_view(enquiries, quotations)

    assert result.loc[0, "Order Confirmed"]
    assert result.loc[0, "Work Order Recorded"]
    assert result.loc[0, "Follow-up Status"] == "Order confirmed — WO recorded"


def test_pending_quotation_is_not_marked_as_lost():
    enquiries = pd.DataFrame(columns=["Client Name", "Enq. No. & Date", "Item"])
    quotations = pd.DataFrame(
        [
            {
                "Quotation No.": "Q3",
                "Client Name": "BluePeak Chemicals",
                "Items": "Bends",
                "Remark": "Under customer review",
                "WO No.": "",
                "Total Value": "185000",
            }
        ]
    )

    result = build_followup_view(enquiries, quotations)

    assert not result.loc[0, "Order Confirmed"]
    assert result.loc[0, "Follow-up Status"] == "Follow-up required"


def test_metrics_use_quotation_values():
    enquiries = pd.DataFrame(
        [
            {
                "Client Name": "Example",
                "Enq. No. & Date": "ENQ-1",
                "Item": "Bends",
            }
        ]
    )

    quotations = pd.DataFrame(
        [
            {
                "Quotation No.": "Q1",
                "Client Name": "Example",
                "Items": "Bends",
                "Remark": "Order Reced",
                "WO No.": "WO-1",
                "Total Value": "125000",
            }
        ]
    )

    metrics = summarize_metrics(enquiries, quotations)

    assert metrics["total_enquiries"] == 1
    assert metrics["total_quotations"] == 1
    assert metrics["total_quotation_value"] == 125000
    assert metrics["orders_confirmed"] == 1
    assert metrics["work_orders_recorded"] == 1
