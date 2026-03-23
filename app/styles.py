import streamlit as st

PALETTE = ["#1A1A1A", "#E8C97A", "#B05C3B", "#4A7C8E", "#8E7DBE", "#5A9E6F"]

CHART = dict(
    paper_bgcolor="#FAFAF8",
    plot_bgcolor="#FAFAF8",
    font_family="JetBrains Mono",
    font_size=10,
    margin=dict(t=20, b=20, l=10, r=10)
)

def inject():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Crimson Pro', Georgia, serif; }
    .stApp { background-color: #FAFAF8; color: #1A1A1A; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { background-color: #1C1C1C; border-right: none; }

    /* Fix: force all sidebar text to be readable */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div { color: #C8C8C8 !important; }

    [data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        color: #888 !important;
        border: none !important;
        border-left: 2px solid transparent !important;
        border-radius: 0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        width: 100% !important;
        text-align: left !important;
        padding: 0.6rem 1.2rem !important;
        margin: 1px 0 !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        color: #FFF !important;
        background: rgba(255,255,255,0.04) !important;
        border-left: 2px solid #888 !important;
    }
    .nav-active button {
        color: #E8C97A !important;
        border-left: 2px solid #E8C97A !important;
        background: rgba(232,201,122,0.07) !important;
    }

    /* ── Lang toggle ── */
    [data-testid="stSidebar"] .stToggle label { color: #888 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.68rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }

    /* ── Typography ── */
    h1 {
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 2.1rem; font-weight: 600; color: #1A1A1A;
        border-bottom: 2px solid #1A1A1A;
        padding-bottom: 0.4rem; margin-bottom: 0.3rem;
    }
    h2 { font-family: 'Crimson Pro', serif; font-size: 1.45rem; font-weight: 600; color: #1A1A1A; margin-top: 2rem; }
    h3 {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem; text-transform: uppercase;
        letter-spacing: 0.1em; color: #666;
        margin-top: 1.8rem; margin-bottom: 0.4rem;
    }
    h4 { font-family: 'Crimson Pro', serif; font-size: 1.1rem; font-weight: 600; color: #1A1A1A; }
    p, li { font-size: 1.05rem; line-height: 1.75; color: #2A2A2A; }
    code { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background: #EDEDEA; padding: 1px 6px; border-radius: 2px; color: #1A1A1A; }

    /* ── Main buttons ── */
    section[data-testid="stMain"] .stButton button {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important; text-transform: uppercase !important;
        letter-spacing: 0.05em !important; background: #1A1A1A !important;
        color: #FAFAF8 !important; border: none !important;
        border-radius: 2px !important; padding: 0.4rem 1.4rem !important;
    }
    section[data-testid="stMain"] .stButton button:hover { background: #333 !important; }

    /* ── KPI ── */
    .kpi { background: #F4F3EE; border-left: 3px solid #1A1A1A; padding: 0.9rem 1.1rem; margin: 0.4rem 0; }
    .kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: #666; margin-bottom: 0.25rem; }
    .kpi-value { font-family: 'Crimson Pro', serif; font-size: 1.6rem; font-weight: 600; color: #1A1A1A; }

    /* ── Fraud cards ── */
    .fraud-card { border: 1px solid #DDD; padding: 1.2rem 1.4rem; margin: 0.8rem 0; background: #FFF; }
    .fc-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: #888; }
    .fc-title { font-family: 'Crimson Pro', serif; font-size: 1.25rem; font-weight: 600; color: #1A1A1A; margin: 0.3rem 0 0.5rem; }
    .fc-body { font-size: 1rem; line-height: 1.65; color: #444; }

    /* ── Highlight band (pre-loaded findings) ── */
    .highlight-band {
        background: #F4F3EE; border-left: 3px solid #E8C97A;
        padding: 0.7rem 1rem; margin: 0.5rem 0;
        font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #1A1A1A;
    }

    hr.rule { border: none; border-top: 1px solid #DDD; margin: 1.8rem 0; }

    /* ── Form labels ── */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSlider"] label,
    div[data-testid="stNumberInput"] label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.05em; color: #666;
    }

    /* ── Expander ── */
    details summary {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem; text-transform: uppercase;
        letter-spacing: 0.05em; color: #666;
    }

    .stDataFrame { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
    .stTabs [data-baseweb="tab"] { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
    """, unsafe_allow_html=True)


def kpi(label: str, value: str):
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>""", unsafe_allow_html=True)


def rule():
    st.markdown('<hr class="rule">', unsafe_allow_html=True)


def fraud_card(tag: str, title: str, body: str):
    st.markdown(f"""
    <div class="fraud-card">
        <div class="fc-tag">{tag}</div>
        <div class="fc-title">{title}</div>
        <div class="fc-body">{body}</div>
    </div>""", unsafe_allow_html=True)


def highlight(text: str):
    st.markdown(f'<div class="highlight-band">⚑ {text}</div>', unsafe_allow_html=True)
