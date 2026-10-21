import base64
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent   # the folder above src/


GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Body font. Only text elements are listed, so the expander arrow icons keep their own font. */
.stApp, .stMarkdown, .stMarkdown p, .stButton button, label,
[data-testid="stSidebar"] a, [data-testid="stExpander"] summary p {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

.block-container { padding-top: 2.5rem; max-width: 1200px; }

/* Soft glow behind the heading */
.hero {
    background:
        radial-gradient(circle at 12% 20%, rgba(29,95,208,0.12), transparent 45%),
        radial-gradient(circle at 85% 0%, rgba(110,162,255,0.20), transparent 40%);
    border-radius: 20px;
    padding: 1.6rem 1.8rem 1.2rem 1.8rem;
    margin-bottom: 1.2rem;
}
.eyebrow { color: #1D5FD0; font-weight: 700; letter-spacing: 0.14em;
           text-transform: uppercase; font-size: 0.8rem; margin-bottom: 0.5rem; }
.hero-title { font-size: 3.3rem; font-weight: 800; line-height: 1.1;
              letter-spacing: -0.02em; color: #111827; margin: 0 0 0.7rem 0; }
.hero-title .accent {
    background: linear-gradient(90deg, #1D5FD0, #4F9BFF);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: #1D5FD0;
}
.hero-sub { font-size: 1.15rem; font-weight: 500; color: #374151; margin-bottom: 0.6rem; }

/* Disclaimer text */
.disclaimer p, .disclaimer li { font-size: 0.98rem; line-height: 1.65; color: #1F2937; }

/* Cards used on later pages */
.card { background: #F2F6FD; border-radius: 14px; padding: 1rem 1.2rem; }
.card-accent { background: #E6EFFD; border: 1px solid #1D5FD0;
               border-radius: 14px; padding: 1rem 1.2rem; }
/* Sidebar menu: blue highlight on hover, solid blue for the current page */
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNavLink"] {
    border-radius: 8px;
    transition: background-color 0.15s ease, color 0.15s ease;
}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(110, 162, 255, 0.28) !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #1D5FD0 !important;
    color: #FFFFFF !important;
}
</style>
"""


def inject_css():
    """Put our CSS on the page. Call once, near the top of app.py."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def svg_as_image_html(relative_path, opacity=1.0):
    """Read an SVG file and return an <img> tag that shows it (no external file needed)."""
    svg_bytes = (PROJECT_ROOT / relative_path).read_bytes()
    encoded = base64.b64encode(svg_bytes).decode()
    return (
        '<img src="data:image/svg+xml;base64,' + encoded + '" '
        'style="width:100%; display:block; opacity:' + str(opacity) + ';">'
    )