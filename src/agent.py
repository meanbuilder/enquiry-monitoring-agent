import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from src.agent import answer_demo_question, explain_with_openai
from src.data_loader import load_sample_data
from src.followup_engine import build_followup_view, summarize_metrics

st.set_page_config(
    page_title="Enquiry Intelligence | Executive Demo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
<style>
.block-container {padding-top:1.6rem; padding-bottom:2.5rem; max-width:1500px;}
[data-testid="stMetric"] {background:#fff; border:1px solid #e5e7eb; padding:16px 18px; border-radius:14px;}
[data-testid="stMetricLabel"] {color:#64748b;} [data-testid="stMetricValue"] {color:#0f172a;}
.hero {padding:1.25rem 1.5rem; border-radius:18px; background:linear-gradient(120deg,#10243e,#1d4ed8); color:white; margin-bottom:1.1rem;}
.hero h1 {color:white; margin:0; font-size:2rem;} .hero p {color:#dbeafe; margin:.45rem 0 0;}
.eyebrow {text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; color:#bfdbfe; font-weight:700;}
.section-title {font-size:1.15rem; font-weight:700; color:#0f172a; margin:.4rem 0 .75rem;}
</style>
""",
    unsafe_allow_html=True,
)

enquiries, quotations = load_sample_data()
followups = build_followup_view(enquiries, quotations)
metrics = summarize_metrics(enquiries, quotations, followups)

with st.sidebar:
    st.markdown("## 📊 Enquiry Intelligence")
    st.caption("Executive monitoring prototype")
    page = st.radio(
        "Navigate",
        ["Executive Overview", "Enquiry Workbench", "Agent Action Centre"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Demo environment**")
    st.success("Synthetic data only")
    st.caption("No company files, external APIs, or real customer data are used.")
    st.divider()
    st.caption("Prototype • Rule-based insights • Human approval required")

st.markdown(
    """
<div class="hero"><div class="eyebrow">Marketing operations · CEO preview</div>
<h1>Enquiry Monitoring &amp; Follow-up</h1>
<p>One view of enquiry flow, quotation outcomes, blockers and recommended next actions.</p></div>
""",
    unsafe_allow_html=True,
)
st.info(
    "DEMO MODE — All records and company names are fictional examples created for this prototype.",
    icon="🔒",
)

if page == "Executive Overview":
    st.markdown(
        '<div class="section-title">Executive snapshot</div>', unsafe_allow_html=True
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total enquiries", f"{metrics['total_enquiries']:,}")
    c2.metric("Quotations issued", f"{metrics['quotations_issued']:,}")
    c3.metric("Orders received", f"{metrics['orders_received']:,}")
    c4.metric("WO preparation check", f"{metrics['wo_check']:,}")
    c5.metric("Needs review", f"{metrics['needs_review']:,}")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown(
            '<div class="section-title">Enquiry pipeline</div>', unsafe_allow_html=True
        )
        pipeline = pd.DataFrame(
            {
                "Stage": ["Enquiry received", "Quotation issued", "Order received"],
                "Records": [
                    metrics["total_enquiries"],
                    metrics["quotations_issued"],
                    metrics["orders_received"],
                ],
            }
        ).set_index("Stage")
        st.bar_chart(pipeline, horizontal=True, height=250)
    with right:
        st.markdown(
            '<div class="section-title">Follow-up priority mix</div>',
            unsafe_allow_html=True,
        )
        priority_order = ["Urgent", "High", "Normal", "Needs review"]
        st.bar_chart(
            followups["Priority"].value_counts().reindex(priority_order, fill_value=0),
            height=250,
        )
    st.markdown(
        '<div class="section-title">Recommended attention list</div>',
        unsafe_allow_html=True,
    )
    attention = followups[
        followups["Priority"].isin(["Urgent", "High", "Needs review"])
    ]
    if attention.empty:
        st.success("No high-priority records in this synthetic dataset.")
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
        "Counts are calculated from the bundled synthetic dataset. They are not business performance claims."
    )

elif page == "Enquiry Workbench":
    st.markdown(
        '<div class="section-title">Search and inspect enquiries</div>',
        unsafe_allow_html=True,
    )
    f1, f2, f3 = st.columns([1.4, 1, 1])
    search = f1.text_input(
        "Search client, item or reference", placeholder="e.g. Northstar"
    )
    priorities = ["All"] + sorted(followups["Priority"].dropna().unique().tolist())
    selected_priority = f2.selectbox("Priority", priorities)
    statuses = ["All"] + sorted(followups["Finding Status"].dropna().unique().tolist())
    selected_status = f3.selectbox("Finding status", statuses)
    view = followups.copy()
    if search.strip():
        mask = (
            view.astype(str)
            .apply(lambda col: col.str.contains(search.strip(), case=False, na=False))
            .any(axis=1)
        )
        view = view[mask]
    if selected_priority != "All":
        view = view[view["Priority"] == selected_priority]
    if selected_status != "All":
        view = view[view["Finding Status"] == selected_status]
    st.caption(f"{len(view)} record(s) match the current filters.")
    st.dataframe(view, use_container_width=True, hide_index=True, height=430)
    with st.expander("Quotation register (synthetic)"):
        st.dataframe(quotations, use_container_width=True, hide_index=True)
    with st.expander("Enquiry register (synthetic)"):
        st.dataframe(enquiries, use_container_width=True, hide_index=True)

else:
    st.markdown(
        '<div class="section-title">Ask the demo assistant</div>',
        unsafe_allow_html=True,
    )
    st.write(
        "Try questions about priority records, orders received, work-order preparation, or unresolved blockers."
    )
    examples = [
        "Which records need attention?",
        "Which customers have placed orders but still need a work order?",
        "What are the main blockers?",
        "Summarize the current pipeline",
    ]
    chosen = st.selectbox("Example questions", ["Choose a sample question…"] + examples)
    question = st.text_input(
        "Your question",
        value="" if chosen == "Choose a sample question…" else chosen,
        placeholder="Ask a question about the synthetic registers",
    )

    if st.button(
        "Analyze records",
        type="primary",
        disabled=not question.strip(),
    ):
        base_result = answer_demo_question(
            question,
            enquiries,
            quotations,
            followups,
            metrics,
        )

        ai_answer = None

        try:
            ai_answer = explain_with_openai(
                question,
                base_result,
                metrics,
            )
        except Exception as exc:
            st.warning(
                "The GPT explanation is unavailable. "
                "Showing the rule-based findings instead."
            )
            st.caption(f"Error type: {type(exc).__name__}")

        st.markdown("### Findings")
        st.write(ai_answer or base_result["answer"])

        if not base_result["records"].empty:
            st.dataframe(
                base_result["records"],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### Suggested next step")
        st.write(base_result["next_step"])

        if ai_answer:
            st.caption(
                "GPT explains the Python findings. "
                "Python remains authoritative for business calculations."
            )
        else:
            st.caption("Rule-based analysis shown; GPT was not available.")
        result = answer_demo_question(
            question, enquiries, quotations, followups, metrics
        )
        st.markdown("### Findings")
        st.write(result["answer"])
        if not result["records"].empty:
            st.dataframe(result["records"], use_container_width=True, hide_index=True)
        st.markdown("### Suggested next step")
        st.write(result["next_step"])
        st.caption(
            "This first version uses transparent Python rules, not a connected LLM. No data is sent to an AI provider."
        )
    st.divider()
    st.markdown("### How this prototype makes decisions")
    st.markdown("""
- A recorded customer order is not automatically treated as a completed work order.
- A blank remark or work-order number is treated as unknown, not proof of a lost enquiry.
- Ambiguous or conflicting information is marked for human review.
- Recommendations are advisory; the prototype does not send emails or modify source registers.
""")

st.divider()
st.caption("Enquiry Intelligence • CEO demo build • Synthetic data only")
