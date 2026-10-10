import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import answer_question
from src.blocker_service import build_blocker_overview, load_blockers
from src.data_loader import load_sample_data
from src.decision_service import build_decision_brief
from src.followup_engine import build_followup_view, summarize_metrics
from src.ui.dashboard import render_dashboard
from src.ui.sidebar import render_sidebar
from src.ui.styles import apply_styles

# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="EnquiryPulse | CEO Command Centre",
    page_icon="⚓",
    layout="wide",
)

apply_styles()


# --------------------------------------------------
# Load application data
# --------------------------------------------------


try:
    enquiries, quotations = load_sample_data()
    followups = build_followup_view(enquiries, quotations)
    metrics = summarize_metrics(enquiries, quotations)

    blockers = load_blockers(ROOT / "sample_data" / "blockers.csv")
    blocker_overview = build_blocker_overview(blockers)

except Exception as exc:
    st.error(f"Could not load the demo registers: {type(exc).__name__}: {exc}")
    st.stop()


except Exception as exc:
    st.error(f"Could not load the demo registers: {type(exc).__name__}: {exc}")
    st.stop()


# --------------------------------------------------
# Shared application header
# --------------------------------------------------

page = render_sidebar()

st.title("EnquiryPulse")
st.caption("Turn enquiry and quotation records into evidence-backed priorities.")

st.warning(
    "DEMO MODE: Use fictional data only. Do not upload confidential "
    "customer or commercial records to a public demo."
)


# --------------------------------------------------
# CEO Overview
# --------------------------------------------------

if page == "CEO Overview":
    render_dashboard(metrics, followups, blocker_overview)


# --------------------------------------------------
# Enquiry Workbench
# --------------------------------------------------

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

    col1, col2 = st.columns(2)

    priority = col1.selectbox("Priority", priority_options)
    status = col2.selectbox("Finding status", status_options)

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

    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Quotation register"):
        st.dataframe(
            quotations,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Enquiry register"):
        st.dataframe(
            enquiries,
            use_container_width=True,
            hide_index=True,
        )


# --------------------------------------------------
# AI Agent
# --------------------------------------------------

elif page == "AI Agent":
    st.subheader("Ask EnquiryPulse")

    st.write(
        "Ask about the pipeline, records needing attention, work-order "
        "checks, documented blockers, or request a follow-up draft."
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
                value=result.get(
                    "draft",
                    result.get("ai_summary", ""),
                ),
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
            "Gemini recommendations are advisory. Python calculates "
            "the metrics and selects the records."
        )


# --------------------------------------------------
# Decision Inbox
# --------------------------------------------------

elif page == "Decision Inbox":
    st.subheader("Decision Inbox")

    st.info(
        "This demo inbox is temporary. Its decisions are not stored "
        "in a shared database, and approving a recommendation sends "
        "no email."
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

            col1, col2, col3 = st.columns(3)

            if col1.button(
                "Approve internal follow-up",
                key=f"approve_{index}",
            ):
                items[index]["status"] = "Approved for internal follow-up"
                st.rerun()

            if col2.button("Reject", key=f"reject_{index}"):
                items[index]["status"] = "Rejected"
                st.rerun()

            if col3.button("Defer", key=f"defer_{index}"):
                items[index]["status"] = "Deferred"
                st.rerun()


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.divider()

st.caption(
    "EnquiryPulse · Gemini-powered demo · Synthetic data · Human verification required"
)
