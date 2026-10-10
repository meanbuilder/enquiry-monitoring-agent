import streamlit as st


def apply_styles():
    """Apply the shared EnquiryPulse visual theme."""
    st.markdown(
        """
        <style>
        .stApp {
            background: #F4F8F8;
            color: #19383B;
        }

        [data-testid="stSidebar"] {
            background: #123F46;
        }

        [data-testid="stSidebar"] * {
            color: #F4FAFA;
        }

        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #D7E5E4;
            border-left: 4px solid #176B70;
            border-radius: 12px;
            padding: 16px;
        }

        h1, h2, h3 {
            color: #123F46;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
