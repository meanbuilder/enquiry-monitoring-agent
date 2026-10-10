"""Streamlit presentation for the CEO Intelligence Cockpit."""

import pandas as pd
import streamlit as st


def _format_inr(value: float) -> str:
    """Format an amount in Indian rupee notation."""
    amount = int(round(value))
    sign = "-" if amount < 0 else ""
    digits = str(abs(amount))

    if len(digits) > 3:
        last_three = digits[-3:]
        remaining = digits[:-3]
        groups = []

        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]

        digits = ",".join(groups + [last_three])
    return f"{sign}₹{digits}"


def render_dashboard(
    metrics: dict,
    followups: pd.DataFrame,
    blocker_overview: dict,
) -> None:
    """Render the executive snapshot and blocker attention queue."""

    st.subheader("Executive snapshot")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total enquiries", metrics["total_enquiries"])
    c2.metric("Quotations issued", metrics["quotations_issued"])
    c3.metric("Orders recorded", metrics["orders_received"])
    c4.metric("Work-order checks", metrics["wo_check"])
    c5.metric("Needs review", metrics["needs_review"])

    left, right = st.columns(2)

    with left:
        st.markdown("#### Pipeline")
        pipeline = pd.DataFrame(
            {
                "Stage": ["Enquiries", "Quotations", "Orders recorded"],
                "Records": [
                    metrics["total_enquiries"],
                    metrics["quotations_issued"],
                    metrics["orders_received"],
                ],
            }
        ).set_index("Stage")
        st.bar_chart(pipeline)

    with right:
        st.markdown("#### Priority mix")
        if "Priority" in followups.columns and not followups.empty:
            st.bar_chart(followups["Priority"].value_counts())
        else:
            st.info("No follow-up priority data is available.")

    st.markdown("#### Existing attention list")
    if not followups.empty and "Priority" in followups.columns:
        attention = followups[
            followups["Priority"].isin(["Urgent", "High", "Needs review"])
        ]
        if attention.empty:
            st.success("No high-priority follow-up records in this dataset.")
        else:
            columns = [
                column
                for column in [
                    "Client Name",
                    "Enquiry Reference",
                    "Item",
                    "Priority",
                    "Blocker / Finding",
                    "Recommended Next Action",
                ]
                if column in attention.columns
            ]
            st.dataframe(
                attention[columns],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No follow-up records are available.")

    st.divider()
    st.subheader("CEO Intelligence Cockpit")
    st.caption(
        "Blocker figures below are based on the synthetic demo register. "
        "Estimated exposure is not confirmed lost revenue."
    )

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Open blockers", blocker_overview["active_blockers"])
    b2.metric("Overdue blockers", blocker_overview["overdue_blockers"])
    b3.metric("Resolved blockers", blocker_overview["resolved_blockers"])
    b4.metric(
        "Estimated exposure",
        _format_inr(blocker_overview["estimated_exposure_inr"]),
    )

    st.markdown("#### Priority action queue")
    active = blocker_overview["attention"]

    if active.empty:
        st.success("No unresolved blockers in the demo register.")
        return

    display = active.copy()
    display["Due date"] = display["due_date"].dt.strftime("%d %b %Y")
    display["Estimated value"] = display["estimated_value_inr"].map(_format_inr)
    display["Overdue"] = (
        display["blocker_id"]
        .isin(blocker_overview["overdue_blocker_ids"])
        .map({True: "Yes", False: "No"})
    )

    display = display.rename(
        columns={
            "blocker_id": "Blocker ID",
            "client_name": "Client",
            "enquiry_reference": "Enquiry / quotation",
            "item": "Item",
            "blocker": "Blocker",
            "owner": "Owner",
            "status": "Status",
            "priority": "Priority",
            "evidence": "Recorded evidence",
            "next_action": "Next action",
        }
    )

    columns = [
        "Blocker ID",
        "Client",
        "Enquiry / quotation",
        "Item",
        "Blocker",
        "Owner",
        "Due date",
        "Overdue",
        "Estimated value",
        "Status",
        "Priority",
        "Recorded evidence",
        "Next action",
    ]

    st.dataframe(
        display[columns],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Management interpretation")
    if blocker_overview["overdue_blockers"]:
        st.warning(
            f"{blocker_overview['overdue_blockers']} unresolved blocker(s) "
            "have due dates before today. Confirm ownership and current status."
        )
    else:
        st.info("No unresolved blocker is overdue according to the demo dates.")

    st.caption(
        "This is a read-only demo queue. Owners, evidence, and commitments "
        "are fictional and have not been verified against real operations."
    )
