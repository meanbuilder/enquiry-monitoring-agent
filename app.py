
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# --------------------------------------------------
# 1. Application setup
# --------------------------------------------------

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.data_loader import load_sample_data
from src.followup_engine import build_followup_view, summarize_metrics
from src.agent import answer_demo_question, explain_with_openai

st.set_page_config(
    page_title="Enquiry Intelligence | Executive Demo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# 2. Styling
# --------------------------------------------------

st.markdown(
    """
    
<style>
:root {
    --primary: #176B70;
    --primary-dark: #123F46;
    --primary-light: #D9EFEC;
    --app-background: #F4F8F8;
    --card-background: #FFFFFF;
    --text-color: #19383B;
    --border-color: #D7E5E4;
}

.stApp {
    background-color: var(--app-background);
    color: var(--text-color);
}

[data-testid="stSidebar"] {
    background-color: var(--primary-dark);
}

[data-testid="stSidebar"] * {
    color: #F4FAFA;
}

.stButton > button[kind="primary"] {
    background-color: var(--primary);
    color: #FFFFFF;
    border: 1px solid var(--primary);
    border-radius: 8px;
}

.stButton > button[kind="primary"]:hover {
    background-color: var(--primary-dark);
    border-color: var(--primary-dark);
}

[data-testid="stMetric"] {
    background-color: var(--card-background);
    border: 1px solid var(--border-color);
    padding: 16px;
    border-radius: 12px;
}


/* KPI metric cards */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D7E5E4;
    border-left: 4px solid #176B70;
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(18, 63, 70, 0.05);
}

[data-testid="stMetricLabel"] {
    color: #526D70;
    font-size: 0.85rem;
    font-weight: 500;
}

[data-testid="stMetricValue"] {
    color: #123F46;
    font-size: 1.8rem;
    font-weight: 700;
}

/* Data tables */
[data-testid="stDataFrame"] {
    border: 1px solid #D7E5E4;
    border-radius: 10px;
    overflow: hidden;
}

/* General headings */
h1, h2, h3 {
    color: #123F46;
}

/* Inputs */
.stTextInput input,
.stSelectbox [data-baseweb="select"] {
    border-color: #B9D5D3;
    border-radius: 8px;
}


</style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 3. Load data and calculate Python findings
# --------------------------------------------------

enquiries, quotations = load_sample_data()

followups = build_followup_view(enquiries, quotations)

metrics = summarize_metrics(
    enquiries,
    quotations,
    followups,
)

# --------------------------------------------------
# 4. Sidebar navigation
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 📊 Enquiry Intelligence")
    st.caption("Executive monitoring prototype")

    page = st.radio(
        "Navigate",
        [
            "Executive Overview",
            "Enquiry Workbench",
            "Agent Action Centre",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("**Demo environment**")
    st.success("Synthetic data only")

    st.caption(
        "OpenAI API is used for AI explanations. "
        "Only summary findings are sent by the agent module."
    )

    st.divider()

    st.caption(
        "Prototype • Python analysis • AI explanations • "
        "Human approval required"
    )

# --------------------------------------------------
# 5. Page header
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">
            Marketing operations · CEO preview
        </div>
        <h1>Enquiry Monitoring &amp; Follow-up</h1>
        <p>
            One view of enquiry flow, quotation outcomes,
            blockers and recommended next actions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "DEMO MODE — All records and company names are fictional "
    "examples created for this prototype.",
    icon="🔒",
)

# --------------------------------------------------
# 6. Executive Overview
# --------------------------------------------------

if page == "Executive Overview":

    st.markdown(
        '<div class="section-title">Executive snapshot</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Total enquiries",
        f"{metrics['total_enquiries']:,}",
    )

    c2.metric(
        "Quotations issued",
        f"{metrics['quotations_issued']:,}",
    )

    c3.metric(
        "Orders received",
        f"{metrics['orders_received']:,}",
    )

    c4.metric(
        "WO preparation check",
        f"{metrics['wo_check']:,}",
    )

    c5.metric(
        "Needs review",
        f"{metrics['needs_review']:,}",
    )

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown(
            '<div class="section-title">Enquiry pipeline</div>',
            unsafe_allow_html=True,
        )

        pipeline = pd.DataFrame(
            {
                "Stage": [
                    "Enquiry received",
                    "Quotation issued",
                    "Order received",
                ],
                "Records": [
                    metrics["total_enquiries"],
                    metrics["quotations_issued"],
                    metrics["orders_received"],
                ],
            }
        ).set_index("Stage")

        st.bar_chart(
            pipeline,
            horizontal=True,
            height=250,
        )

    with right:
        st.markdown(
            '<div class="section-title">Follow-up priority mix</div>',
            unsafe_allow_html=True,
        )

        priority_order = [
            "Urgent",
            "High",
            "Normal",
            "Needs review",
        ]

        priority_counts = (
            followups["Priority"]
            .value_counts()
            .reindex(priority_order, fill_value=0)
        )

        st.bar_chart(
            priority_counts,
            height=250,
        )

    st.markdown(
        '<div class="section-title">Recommended attention list</div>',
        unsafe_allow_html=True,
    )

    attention = followups[
        followups["Priority"].isin(
            ["Urgent", "High", "Needs review"]
        )
    ]

    if attention.empty:
        st.success(
            "No high-priority records in this synthetic dataset."
        )
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

    st.caption(
        "Counts are calculated from the bundled synthetic dataset. "
        "They are not business performance claims."
    )

# --------------------------------------------------
# 7. Enquiry Workbench
# --------------------------------------------------

elif page == "Enquiry Workbench":

    st.markdown(
        '<div class="section-title">Search and inspect enquiries</div>',
        unsafe_allow_html=True,
    )

    f1, f2, f3 = st.columns([1.4, 1, 1])

    search = f1.text_input(
        "Search client, item or reference",
        placeholder="e.g. Northstar",
    )

    priorities = ["All"] + sorted(
        followups["Priority"].dropna().unique().tolist()
    )

    selected_priority = f2.selectbox(
        "Priority",
        priorities,
    )

    statuses = ["All"] + sorted(
        followups["Finding Status"].dropna().unique().tolist()
    )

    selected_status = f3.selectbox(
        "Finding status",
        statuses,
    )

    view = followups.copy()

    if search.strip():
        mask = (
            view.astype(str)
            .apply(
                lambda col: col.str.contains(
                    search.strip(),
                    case=False,
                    na=False,
                    regex=False,
                )
            )
            .any(axis=1)
        )

        view = view[mask]

    if selected_priority != "All":
        view = view[
            view["Priority"] == selected_priority
        ]

    if selected_status != "All":
        view = view[
            view["Finding Status"] == selected_status
        ]

    st.caption(
        f"{len(view)} record(s) match the current filters."
    )

    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        height=430,
    )

    with st.expander("Quotation register (synthetic)"):
        st.dataframe(
            quotations,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Enquiry register (synthetic)"):
        st.dataframe(
            enquiries,
            use_container_width=True,
            hide_index=True,
        )

# --------------------------------------------------
# 8. Agent Action Centre
# --------------------------------------------------

else:

    st.markdown(
        '<div class="section-title">Ask the AI-assisted agent</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Ask questions about priority records, customer orders, "
        "work-order preparation, blockers or the enquiry pipeline."
    )

    examples = [
        "Which records need attention?",
        "Which customers have placed orders but still need a work order?",
        "What are the main blockers?",
        "Summarize the current pipeline",
    ]

    chosen = st.selectbox(
        "Example questions",
        ["Choose a sample question…"] + examples,
    )

    question = st.text_input(
        "Your question",
        value=(
            ""
            if chosen == "Choose a sample question…"
            else chosen
        ),
        placeholder="Ask a question about the synthetic registers",
    )

    if st.button(
        "Analyze records",
        type="primary",
        disabled=not question.strip(),
    ):

        # Step 1: Python calculates findings.
        with st.spinner("Analysing records with Python..."):

            result = answer_demo_question(
                question,
                enquiries,
                quotations,
                followups,
                metrics,
            )

        st.markdown("### Python Findings")

        st.write(result["answer"])

        result_records = result.get("records")

        if (
            isinstance(result_records, pd.DataFrame)
            and not result_records.empty
        ):
            st.dataframe(
                result_records,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No matching records were returned.")

        st.markdown("### Recommended Next Step")

        st.write(result["next_step"])

        # Step 2: OpenAI explains the Python findings.
        st.divider()

        st.markdown("### AI Explanation")

        with st.spinner("Generating AI explanation..."):

            ai_answer = explain_with_openai(
                question,
                result,
                metrics,
            )

        st.markdown(ai_answer)

        st.caption(
            "Python calculates the findings. OpenAI explains them. "
            "Recommendations require human review."
        )

    st.divider()

    st.markdown("### How this prototype makes decisions")

    st.markdown(
        """
        - A recorded customer order is not automatically treated as a completed work order.
        - A blank remark or work-order number is treated as unknown, not proof of a lost enquiry.
        - Ambiguous or conflicting information is marked for human review.
        - Python remains responsible for the calculations and rule-based findings.
        - OpenAI explains the supplied findings; it does not independently verify the source registers.
        - Recommendations are advisory. The prototype does not send emails or modify source registers.
        """
    )

# --------------------------------------------------
# 9. Footer
# --------------------------------------------------

st.divider()

st.caption(
    "Enquiry Intelligence • CEO demo build • Synthetic data only"
)
