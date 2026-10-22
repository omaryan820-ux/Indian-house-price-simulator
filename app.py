import streamlit as st

from src.branding import APP_NAME
from src.ui_components import PROJECT_ROOT, inject_css

# Must be the first Streamlit call
st.set_page_config(page_title=APP_NAME, page_icon="🏠", layout="wide")

inject_css()

st.logo(str(PROJECT_ROOT / "assets" / "logo.svg"),
        icon_image=str(PROJECT_ROOT / "assets" / "logo_icon.svg"), size="large")

pages = [
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/simulator.py", title="Simulator"),
    st.Page("views/analysis.py", title="Analysis"),
    st.Page("views/compare.py", title="Compare"),
    st.Page("views/accuracy.py", title="Accuracy & Assumptions"),
]

navigation = st.navigation(pages)
navigation.run()