import pandas as pd
import streamlit as st


def render_dashboard(metrics, followups):
    """Render the CEO Overview page."""

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
                "Stage": [
                    "Enquiries",
                    "Quotations",
                    "Orders recorded",
                ],
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

        counts = followups["Priority"].value_counts()
        st.bar_chart(counts)

    st.markdown("#### Recommended attention list")

    attention = followups[
        followups["Priority"].isin(["Urgent", "High", "Needs review"])
    ]

    if attention.empty:
        st.success("No high-priority records in this dataset.")
    else:
        columns = [
            "Client Name",
            "Enquiry Reference",
            "Item",
            "Priority",
            "Blocker / Finding",
            "Recommended Next Action",
        ]

        st.dataframe(
            attention[columns],
            use_container_width=True,
            hide_index=True,
        )
