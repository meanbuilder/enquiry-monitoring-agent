"""Build a structured CEO decision brief."""


def build_decision_brief(question: str, result: dict, metrics: dict) -> dict:
    records = result.get("records")

    if records is not None and hasattr(records, "empty") and not records.empty:
        clients = records["Client Name"].astype(str).drop_duplicates().head(5).tolist()

        evidence = (
            f"{len(records)} attention record(s). "
            f"Clients: {', '.join(clients) if clients else 'not identified'}."
        )
    else:
        evidence = str(result.get("evidence", "No matching records returned."))

    return {
        "question": question or "Management review",
        "evidence": evidence,
        "recommendation": result.get(
            "ai_summary",
            result.get("answer", "Review the relevant source records."),
        ),
        "uncertainty": (
            "This brief uses only the available registers. "
            "Missing remarks or work-order references do not prove "
            "that an order was lost."
        ),
        "next_action": result.get(
            "next_step",
            "Assign an owner and verify the facts with the responsible team.",
        ),
        "metrics_snapshot": dict(metrics),
    }
