import streamlit as st

def setup_page():
    st.set_page_config(
        page_title="Refinitiv Stock Screener",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("Refinitiv Stock Screener")

def apply_custom_css():
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        .stApp > header {display: none;}
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 70vw !important;
            width: 70vw !important;
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 50px;
        }
        .stDataFrame {
            width: 100%;
        }
        .stSelectbox, .stMultiselect {
            width: 100%;
        }
        .stButton > button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)
