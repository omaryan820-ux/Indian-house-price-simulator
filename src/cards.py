import streamlit as st

CARD_CSS = """
<style>
.vcard { background:#F2F6FD; border-radius:14px; padding:1.1rem 1.3rem; height:100%; }
.vcard.accent { background:#E6EFFD; border:2px solid #1D5FD0; }
.vcard .vtitle { font-size:0.82rem; font-weight:600; color:#4B5563; text-transform:uppercase; letter-spacing:0.06em; }
.vcard .vvalue { font-size:2.2rem; font-weight:800; color:#111827; line-height:1.2; margin:0.2rem 0; }
.vcard.accent .vvalue { color:#1D5FD0; }
.vcard .vnote { font-size:0.88rem; color:#4B5563; }
.badge { display:inline-block; font-size:0.75rem; font-weight:700; padding:2px 10px; border-radius:999px; margin-left:8px; }
.badge.High { background:#DCEBFF; color:#143F8C; }
.badge.Medium { background:#FFF1D6; color:#8A5200; }
.badge.Low { background:#FDE3E3; color:#9B1C1C; }
.rbar { position:relative; height:10px; background:#C7DBFA; border-radius:999px; margin:0.9rem 0 0.3rem 0; }
.rbar .dot { position:absolute; top:-4px; width:18px; height:18px; background:#1D5FD0; border:3px solid #FFFFFF; border-radius:50%; transform:translateX(-50%); }
.rlabels { display:flex; justify-content:space-between; font-size:0.85rem; color:#374151; }
.mcard { background:#FFFFFF; border:1px solid #E5E7EB; border-left:5px solid #1D5FD0; border-radius:12px; padding:0.9rem 1rem; height:100%; }
.mcard.red { border-left-color:#C53030; }
.mcard.amber { border-left-color:#D98A00; }
.mcard .mlabel { font-size:0.8rem; font-weight:600; color:#4B5563; }
.mcard .mvalue { font-size:1.55rem; font-weight:800; color:#111827; margin:0.15rem 0; }
.mcard.red .mvalue { color:#B42318; }
.mcard.amber .mvalue { color:#9A5B00; }
.mcard .mnote { font-size:0.8rem; color:#6B7280; }
.verdict { border-radius:12px; padding:1rem 1.2rem; margin:1rem 0; }
.verdict.red { background:#FDECEC; border:1px solid #F5B5B5; color:#7F1D1D; }
.verdict.blue { background:#E6EFFD; border:1px solid #B7CFF5; color:#143F8C; }
.verdict.amber { background:#FFF4E0; border:1px solid #F3CF8E; color:#6B4200; }
.verdict.green { background:#E8F6EC; border:1px solid #A7DDB5; color:#14532D; }
.verdict .vh { font-weight:800; font-size:1.05rem; margin-bottom:0.2rem; }
</style>
"""


def inject_card_css():
    st.markdown(CARD_CSS, unsafe_allow_html=True)


def value_card(title, value, note, accent=False, badge=None):
    cls = "vcard accent" if accent else "vcard"
    badge_html = ""
    if badge:
        badge_html = '<span class="badge ' + badge + '">' + badge + " confidence</span>"
    html = (
        '<div class="' + cls + '"><div class="vtitle">' + title + badge_html + "</div>"
        '<div class="vvalue">' + value + "</div>"
        '<div class="vnote">' + note + "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def range_bar(low_text, high_text, position_pct):
    position_pct = max(0, min(100, position_pct))
    html = (
        '<div class="rbar"><div class="dot" style="left:' + format(position_pct, ".0f") + '%"></div></div>'
        '<div class="rlabels"><span>' + low_text + "</span><span>" + high_text + "</span></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_card(label, value, note, tone="neutral"):
    cls = "mcard"
    if tone in ("red", "amber"):
        cls = "mcard " + tone
    html = (
        '<div class="' + cls + '"><div class="mlabel">' + label + "</div>"
        '<div class="mvalue">' + value + "</div>"
        '<div class="mnote">' + note + "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def verdict_banner(level, headline, detail):
    html = (
        '<div class="verdict ' + level + '"><div class="vh">' + headline + "</div>"
        "<div>" + detail + "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)