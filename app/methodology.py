import streamlit as st
from styles import rule, fraud_card, kpi
from i18n import t

def render():
    st.markdown(f"# {t('meth_title')}")
    st.markdown(t("meth_intro"))
    rule()

    st.markdown(f"## {t('meth_patterns')}")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        fraud_card(
            "Pattern 01 · Compra Ágil" if st.session_state.get("lang") == "en" else "Patrón 01 · Compra Ágil",
            "Contract fragmentation" if st.session_state.get("lang") == "en" else "Fraccionamiento de contratos",
            ("The law allows direct purchases under 100 UTM (~$6.6M CLP) without tender. "
             "Some agencies evade this limit by making <em>multiple small purchases to the same "
             "vendor in the same month</em>, adding up to amounts that should have been publicly tendered.")
            if st.session_state.get("lang") == "en" else
            ("La ley permite compras directas menores a 100 UTM (~$6,6M CLP) sin licitación. "
             "Algunos organismos evaden ese límite haciendo <em>varias compras pequeñas al mismo "
             "proveedor en el mismo mes</em>, sumando montos que debían licitarse públicamente.")
        )
        fraud_card(
            "Pattern 03 · Contract network" if st.session_state.get("lang") == "en" else "Patrón 03 · Red de contratos",
            "Structural dominance" if st.session_state.get("lang") == "en" else "Dominancia estructural",
            ("Using PageRank — the same algorithm Google uses to rank pages — we identify "
             "vendors with disproportionate power in the network. A high score means too many "
             "agencies depend on the same vendor, enabling monopolistic practices.")
            if st.session_state.get("lang") == "en" else
            ("Usando PageRank — el algoritmo que usa Google para rankear páginas — identificamos "
             "proveedores con poder desproporcionado en la red. Un score alto indica que demasiados "
             "organismos dependen del mismo proveedor, facilitando prácticas monopólicas.")
        )
    with c2:
        fraud_card(
            "Pattern 02 · Direct Deal" if st.session_state.get("lang") == "en" else "Patrón 02 · Trato Directo",
            "Institutional capture" if st.session_state.get("lang") == "en" else "Captura institucional",
            ("When an agency directs more than 40% of its Direct Deal budget to a single vendor, "
             "that's not a coincidence: it's a dependency relationship. It may indicate that the "
             "private entity has undue influence over the agency's purchasing decisions.")
            if st.session_state.get("lang") == "en" else
            ("Cuando un organismo destina más del 40% de su presupuesto de Trato Directo "
             "a un único proveedor, eso no es coincidencia: es una relación de dependencia. "
             "Puede indicar que ese privado tiene influencia indebida sobre las decisiones de compra.")
        )
        fraud_card(
            "Pattern 04 · Public health" if st.session_state.get("lang") == "en" else "Patrón 04 · Salud pública",
            "Bidding rings" if st.session_state.get("lang") == "en" else "Anillos de licitación",
            ("Two companies that appear together in contracts with multiple hospitals, "
             "always with high amounts, may be coordinating to split the market. "
             "What looks like competitive bidding may be a private agreement.")
            if st.session_state.get("lang") == "en" else
            ("Dos empresas que aparecen juntas en contratos de múltiples hospitales, "
             "siempre con montos altos, pueden estar coordinadas para repartirse el mercado. "
             "Lo que parece una licitación competitiva puede ser un acuerdo entre privados.")
        )

    rule()
    st.markdown(f"## {t('meth_how')}")
    s1, s2, s3 = st.columns(3)
    for col, lbl_key, txt_key in [
        (s1, "meth_step1_label", "meth_step1_body"),
        (s2, "meth_step2_label", "meth_step2_body"),
        (s3, "meth_step3_label", "meth_step3_body"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi">
                <div class="kpi-label">{t(lbl_key)}</div>
                <div style="font-size:1rem;line-height:1.65;color:#444;margin-top:0.4rem">{t(txt_key)}</div>
            </div>""", unsafe_allow_html=True)

    rule()
    st.markdown(f"## {t('meth_modalities')}")
    if st.session_state.get("lang") == "en":
        st.markdown("""
        | Code | Name | Description | Risk |
        |------|------|-------------|------|
        | `AG` | Compra Ágil | No tender, up to 100 UTM | High — subject to fragmentation |
        | `TD` | Direct Deal | No competition, requires justification | High — subject to capture |
        | `LE` | Public Tender | Open competitive process | Low |
        | `L1` | Private Tender | Selected invitees | Medium |
        """)
    else:
        st.markdown("""
        | Código | Nombre | Descripción | Riesgo |
        |--------|--------|-------------|--------|
        | `AG` | Compra Ágil | Sin licitación, hasta 100 UTM | Alto — sujeto a fraccionamiento |
        | `TD` | Trato Directo | Sin concurso, requiere justificación | Alto — sujeto a captura |
        | `LE` | Licitación Pública | Proceso abierto y competitivo | Bajo |
        | `L1` | Licitación Privada | Invitados seleccionados | Medio |
        """)
