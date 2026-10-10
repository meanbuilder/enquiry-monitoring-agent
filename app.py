import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import answer_question
from src.data_loader import load_sample_data
from src.decision_service import build_decision_brief
from src.followup_engine import build_followup_view, summarize_metrics

st.set_page_config(
    page_title="EnquiryPulse | CEO Command Centre",
    page_icon="⚓",
    layout="wide",
)

st.markdown(
    """
<style>
.stApp { background: #F4F8F8; color: #19383B; }
[data-testid="stSidebar"] { background: #123F46; }
[data-testid="stSidebar"] * { color: #F4FAFA; }
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #D7E5E4;
    border-left: 4px solid #176B70;
    border-radius: 12px;
    padding: 16px;
}
h1, h2, h3 { color: #123F46; }
</style>
""",
    unsafe_allow_html=True,
)

try:
    enquiries, quotations = load_sample_data()
    followups = build_followup_view(enquiries, quotations)
    metrics = summarize_metrics(enquiries, quotations, followups)
except Exception as exc:
    st.error(f"Could not load the demo registers: {type(exc).__name__}: {exc}")
    st.stop()

with st.sidebar:
    st.markdown("## ⚓ EnquiryPulse")
    st.caption("AI-powered CEO Command Centre")

    page = st.radio(
        "Navigate",
        [
            "CEO Overview",
            "Enquiry Workbench",
            "AI Agent",
            "Decision Inbox",
        ],
    )

    st.divider()
    st.success("Synthetic demo data only")
    st.caption("Gemini AI · Python analysis · Human approval")

st.title("EnquiryPulse")
st.caption("Turn enquiry and quotation records into evidence-backed priorities.")

st.warning(
    "DEMO MODE: Use fictional data only. Do not upload confidential "
    "customer or commercial records to a public demo."
)

if page == "CEO Overview":
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
        st.dataframe(
            attention[
                [
                    "Client Name",
                    "Enquiry Reference",
                    "Item",
                    "Priority",
                    "Blocker / Finding",
                    "Recommended Next Action",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

elif page == "Enquiry Workbench":
    st.subheader("Search and inspect records")

    search = st.text_input(
        "Search client, item or reference",
        placeholder="Enter a client or item",
    )

    priority_options = ["All"] + sorted(
        followups["Priority"].dropna().astype(str).unique().tolist()
    )
    status_options = ["All"] + sorted(
        followups["Finding Status"].dropna().astype(str).unique().tolist()
    )

    c1, c2 = st.columns(2)
    priority = c1.selectbox("Priority", priority_options)
    status = c2.selectbox("Finding status", status_options)

    view = followups.copy()

    if search.strip():
        mask = (
            view.astype(str)
            .apply(
                lambda column: column.str.contains(
                    search.strip(),
                    case=False,
                    na=False,
                    regex=False,
                )
            )
            .any(axis=1)
        )
        view = view[mask]

    if priority != "All":
        view = view[view["Priority"] == priority]

    if status != "All":
        view = view[view["Finding Status"] == status]

    st.caption(f"{len(view)} matching record(s).")
    st.dataframe(view, use_container_width=True, hide_index=True)

    with st.expander("Quotation register"):
        st.dataframe(quotations, use_container_width=True, hide_index=True)

    with st.expander("Enquiry register"):
        st.dataframe(enquiries, use_container_width=True, hide_index=True)

elif page == "AI Agent":
    st.subheader("Ask EnquiryPulse")

    st.write(
        "Ask about the pipeline, records needing attention, work-order checks, "
        "documented blockers, or request a follow-up draft."
    )

    examples = [
        "Summarize the current pipeline",
        "Which records need attention?",
        "Which orders need a work-order check?",
        "Find records for Northstar",
        "Draft a follow-up email for Northstar",
        "Prepare a decision brief",
    ]

    example = st.selectbox(
        "Example questions",
        ["Choose an example"] + examples,
    )

    default_question = "" if example == "Choose an example" else example

    question = st.text_input(
        "Your question",
        value=default_question,
        key="agent_question",
    )

    if st.button(
        "Analyze with Gemini",
        type="primary",
        disabled=not question.strip(),
    ):
        with st.spinner("Analyzing available records..."):
            result = answer_question(
                question,
                enquiries,
                quotations,
                followups,
                metrics,
            )

        st.session_state["last_agent_result"] = result
        st.session_state["last_agent_question"] = question

    result = st.session_state.get("last_agent_result")

    if result:
        st.markdown("#### Python findings")
        st.write(result.get("answer", "No answer available."))

        if result.get("tool"):
            st.caption(f"Analysis tool: {result['tool']}")

        records = result.get("records")

        if isinstance(records, pd.DataFrame) and not records.empty:
            st.markdown("#### Evidence records")
            st.dataframe(
                records,
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### Recommended next step")
        st.write(result.get("next_step", "Verify the source records."))

        if result.get("ai_summary"):
            st.markdown("#### Gemini explanation")
            st.write(result["ai_summary"])

        if result.get("action_kind") == "draft":
            st.text_area(
                "Follow-up draft — review before sending",
                value=result.get("draft", result.get("ai_summary", "")),
                height=240,
            )

        if result.get("action_kind") == "decision":
            brief = build_decision_brief(
                st.session_state.get("last_agent_question", ""),
                result,
                metrics,
            )

            st.markdown("#### CEO decision brief")
            st.write("**Question:**", brief["question"])
            st.write("**Evidence:**", brief["evidence"])
            st.write("**Recommendation:**", brief["recommendation"])
            st.write("**Risk / uncertainty:**", brief["uncertainty"])
            st.write("**Proposed next action:**", brief["next_action"])

            if st.button("Add to Decision Inbox"):
                st.session_state.setdefault("decision_items", [])
                st.session_state["decision_items"].append(
                    {
                        **brief,
                        "status": "Pending review",
                    }
                )
                st.success("Added to this session's Decision Inbox.")

        st.caption(
            "Gemini recommendations are advisory. Python calculates the metrics "
            "and selects the records."
        )

elif page == "Decision Inbox":
    st.subheader("Decision Inbox")

    st.info(
        "This demo inbox is temporary. Its decisions are not stored in a "
        "shared database, and approving a recommendation sends no email."
    )

    items = st.session_state.get("decision_items", [])

    if not items:
        st.write("No decision briefs yet. Create one from the AI Agent section.")

    for index, item in enumerate(items):
        with st.container(border=True):
            st.markdown(f"**{index + 1}. {item.get('question', 'Decision brief')}**")
            st.write(item.get("recommendation", ""))
            st.write("**Evidence:**", item.get("evidence", ""))
            st.write("**Uncertainty:**", item.get("uncertainty", ""))
            st.caption(f"Status: {item.get('status', 'Pending review')}")

            a, b, c = st.columns(3)

            if a.button("Approve internal follow-up", key=f"approve_{index}"):
                items[index]["status"] = "Approved for internal follow-up"
                st.rerun()

            if b.button("Reject", key=f"reject_{index}"):
                items[index]["status"] = "Rejected"
                st.rerun()

            if c.button("Defer", key=f"defer_{index}"):
                items[index]["status"] = "Deferred"
                st.rerun()

st.divider()
st.caption(
    "EnquiryPulse · Gemini-powered demo · Synthetic data · Human verification required"
)
