import pandas as pd
from src.ai_tools import execute_tool


def test_unknown_tool_cannot_execute_arbitrary_action():
    empty = pd.DataFrame(columns=["Priority", "Client Name"])

    result = execute_tool(
        "arbitrary_command",
        {},
        empty,
        empty,
        empty,
        {"total_enquiries": 2},
    )

    assert result["tool"] == "pipeline_summary"
    assert result["evidence"]["total_enquiries"] == 2


def test_search_tool_matches_client_name():
    records = pd.DataFrame(
        [
            {
                "Client Name": "Northstar Systems",
                "Priority": "High",
                "Finding Status": "Review",
                "Blocker / Finding": "Awaiting drawing",
            }
        ]
    )

    result = execute_tool(
        "search_records",
        {"query": "Northstar"},
        records,
        records,
        records,
        {"total_enquiries": 1},
    )

    assert len(result["records"]) == 1
    assert result["records"].iloc[0]["Client Name"] == "Northstar Systems"
