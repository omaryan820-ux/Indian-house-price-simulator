import streamlit as st

from src.ui_components import svg_as_image_html
from src.branding import APP_NAME, APP_SUBTITLE
st.markdown(
    """
    <div class="hero">
        <div class="brand">""" + APP_NAME + """ <span>· """ + APP_SUBTITLE + """</span></div>
        <div class="hero-title">The real cost of a <span class="accent">metro home</span></div>
        <div class="hero-sub">Estimate it. Finance it. Stress-test it.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Please read: where the numbers come from"):
    st.markdown(
        """
<div class="disclaimer">

**Data.** The price model is trained on a public housing dataset from Kaggle covering six metros:
Bangalore, Chennai, Delhi NCR, Hyderabad, Kolkata and Mumbai. The dataset was last updated about
six years ago, so its prices reflect that period, not today's market.

**2026 value.** To bring prices to 2026, we apply our own city-wise yearly growth rates.
These are estimates built from published market reports, not model output, and you can see
the rate used next to every result.

**Accuracy.** The typical error of the model is about 12% in Hyderabad and about 37% in Kolkata.
It works best for ordinary flats in mainstream localities. It is **not reliable for luxury or
prime areas** 
Treat every price as a rough range, not a quote.

**Finance.** Loan, rent and return figures use simple assumptions that you can change.
This is a learning tool and not financial, legal or investment advice.

</div>
""",
        unsafe_allow_html=True,
    )

from src.live_mode import MODE_INVEST, MODE_LIVE

st.markdown("**What do you want to do?**")
left, right = st.columns(2)
with left:
    if st.button("I want to live in it →", type="primary", width="stretch"):
        st.session_state.setdefault("inputs", {})["mode"] = MODE_LIVE
        st.switch_page("views/simulator.py")
with right:
    if st.button("I want to invest →", width="stretch"):
        st.session_state.setdefault("inputs", {})["mode"] = MODE_INVEST
        st.switch_page("views/simulator.py")

st.write("")
st.markdown(svg_as_image_html("assets/roofline.svg"), unsafe_allow_html=True)