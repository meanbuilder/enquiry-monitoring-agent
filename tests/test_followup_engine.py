import pandas as pd
from src.followup_engine import build_followup_view

def test_order_received_without_wo_is_high_priority():
    enquiries = pd.DataFrame(columns=["Client Name", "ENQ Review"])
    quotations = pd.DataFrame([{"Quotation No.": "Q-1", "Quotation Date": "2026-10-01", "Client Name": "Example Ltd", "Items": "Bends", "Remark": "Order Reced", "WO No.": "", "Total Value": 1000}])
    view = build_followup_view(enquiries, quotations)
    assert view.iloc[0]["Priority"] == "High"
    assert view.iloc[0]["Finding Status"] == "Order received — WO check"

def test_blank_remark_and_wo_are_unknown_not_lost():
    enquiries = pd.DataFrame(columns=["Client Name", "ENQ Review"])
    quotations = pd.DataFrame([{"Quotation No.": "Q-2", "Quotation Date": "2026-10-01", "Client Name": "Example Ltd", "Items": "Bends", "Remark": "", "WO No.": "", "Total Value": 1000}])
    view = build_followup_view(enquiries, quotations)
    assert view.iloc[0]["Priority"] == "Needs review"
    assert "cannot be inferred" in view.iloc[0]["Blocker / Finding"]
