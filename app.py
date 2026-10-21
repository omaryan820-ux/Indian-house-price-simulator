import streamlit as st

from src.ui_components import inject_css

# Must be the first Streamlit call
st.set_page_config(page_title="Indian House Price Simulator", page_icon="🏠", layout="wide")

inject_css()

pages = [
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/simulator.py", title="Simulator"),
    st.Page("views/analysis.py", title="Analysis"),
    st.Page("views/compare.py", title="Compare"),
    st.Page("views/accuracy.py", title="Accuracy & Assumptions"),
]

navigation = st.navigation(pages)
navigation.run()