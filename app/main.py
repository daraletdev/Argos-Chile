import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import styles
from i18n import t
import methodology, explorer, risk

st.set_page_config(
    page_title="Argos Forensic",
    layout="wide",
    initial_sidebar_state="expanded"
)

styles.inject()

if "page" not in st.session_state:
    st.session_state.page = "Metodología"
if "lang" not in st.session_state:
    st.session_state.lang = "es"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.5rem 1.2rem 0.8rem">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;
                    letter-spacing:0.15em;text-transform:uppercase;color:#555;margin-bottom:0.3rem">
            Sistema Auditoría
        </div>
        <div style="font-family:'Crimson Pro',serif;font-size:1.55rem;font-weight:600;color:#F0F0F0">
            Argos
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:#555">
            Chile · 2026
        </div>
    </div>
    <hr style="border:none;border-top:1px solid #2E2E2E;margin:0 0 0.8rem">
    """, unsafe_allow_html=True)

    nav = {
        "Metodología": t("nav_methodology"),
        "Explorador":  t("nav_explorer"),
        "Riesgo":      t("nav_risk"),
    }

    for key, label in nav.items():
        active = st.session_state.page == key
        if active:
            st.markdown('<div class="nav-active">', unsafe_allow_html=True)
        if st.button(label, key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()
        if active:
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <hr style="border:none;border-top:1px solid #2E2E2E;margin:1.5rem 0 0.8rem">
    """, unsafe_allow_html=True)

    # Language toggle
    lang_label = "🌐 English" if st.session_state.lang == "es" else "🌐 Español"
    if st.button(lang_label, key="lang_btn"):
        st.session_state.lang = "en" if st.session_state.lang == "es" else "es"
        st.rerun()

    st.markdown("""
    <hr style="border:none;border-top:1px solid #2E2E2E;margin:0.8rem 0">
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:#3A3A3A;padding:0 1.2rem 1rem">
        Fuente: Mercado Público<br>Grafo: Neo4j Gold Layer<br>Datos: 2025
    </div>
    """, unsafe_allow_html=True)

# ── Router ────────────────────────────────────────────────────────────────────
pages = {
    "Metodología": methodology.render,
    "Explorador":  explorer.render,
    "Riesgo":      risk.render,
}

pages[st.session_state.page]()
