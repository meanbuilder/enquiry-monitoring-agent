import streamlit as st

PAGES = [
    "CEO Overview",
    "Enquiry Workbench",
    "AI Agent",
    "Decision Inbox",
]


def render_sidebar():
    """Render the sidebar and return the selected page."""
    with st.sidebar:
        st.markdown("## ⚓ EnquiryPulse")
        st.caption("AI-powered CEO Command Centre")

        page = st.radio(
            "Navigate",
            PAGES,
        )

        st.divider()
        st.success("Synthetic demo data only")
        st.caption("Gemini AI · Python analysis · Human approval")

    return page
