import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import run_query
from fmt import truncate, clp
from styles import rule, CHART, highlight
from i18n import t

# ── Queries ───────────────────────────────────────────────────────────────────

Q_FRAGMENTATION = """
MATCH (u:UnidadCompra)-[:EMITIO]->(oc:OrdenCompra_Item {Modalidad: 'AG'})-[:ADJUDICADA_A]->(p:Proveedor)
WITH u.UnidadCompra AS Organismo, p.Nombre AS Proveedor,
     oc.Fecha.month AS Mes, count(oc) AS N_Ordenes, sum(oc.Monto) AS Total_CLP
WHERE N_Ordenes > 1 AND Total_CLP > $umbral
RETURN Organismo, Proveedor, Mes, N_Ordenes, Total_CLP
ORDER BY Total_CLP DESC
"""

Q_CAPTURE = """
MATCH (u:UnidadCompra)-[:EMITIO]->(oc:OrdenCompra_Item {Modalidad: 'TD'})-[:ADJUDICADA_A]->(p:Proveedor)
WITH u, p, sum(oc.Monto) AS mp
MATCH (u)-[:EMITIO]->(td:OrdenCompra_Item {Modalidad: 'TD'})
WITH u, p, mp, sum(td.Monto) AS total_td
WHERE total_td > $min_budget
WITH u, p, mp, total_td, (mp / total_td) * 100 AS conc
WHERE conc > $pct
RETURN u.UnidadCompra AS Organismo, p.Nombre AS Proveedor,
       round(conc, 1) AS Concentración_Pct, total_td AS Presupuesto_TD_CLP
ORDER BY Concentración_Pct DESC
"""

Q_PAGERANK = """
MATCH (p:Proveedor) WHERE p.pagerank_score IS NOT NULL
RETURN p.Nombre AS Proveedor, p.pagerank_score AS Score
ORDER BY Score DESC LIMIT $n
"""

Q_EXCLUSIVITY = """
MATCH (p:Proveedor)<-[:ADJUDICADA_A]-(oc:OrdenCompra_Item)
WITH p, sum(oc.Monto) AS ingresos_totales
WHERE ingresos_totales > $min_rev
MATCH (u:UnidadCompra)-[:EMITIO]->(oc2:OrdenCompra_Item {Modalidad: 'TD'})-[:ADJUDICADA_A]->(p)
WITH p, u, ingresos_totales, sum(oc2.Monto) AS ingresos_td
WHERE ingresos_td > (ingresos_totales * 0.95)
RETURN p.Nombre AS Proveedor, u.UnidadCompra AS Organismo_Principal,
       ingresos_td AS Ingresos_TD_CLP, ingresos_totales AS Ingresos_Totales_CLP
ORDER BY Ingresos_TD_CLP DESC LIMIT 20
"""

Q_BIDDING_RINGS = """
MATCH (u:UnidadCompra {Sector: 'Salud'})-[:EMITIO]->(oc1:OrdenCompra_Item)-[:ADJUDICADA_A]->(p1:Proveedor)
WHERE oc1.Monto > $min_monto
MATCH (u)-[:EMITIO]->(oc2:OrdenCompra_Item)-[:ADJUDICADA_A]->(p2:Proveedor)
WHERE elementId(p1) < elementId(p2) AND oc2.Monto > $min_monto
WITH p1, p2, count(DISTINCT u) AS org_compartidos, sum(oc1.Monto + oc2.Monto) AS mercado_total
WHERE org_compartidos >= $min_shared
RETURN p1.Nombre AS Proveedor_A, p2.Nombre AS Proveedor_B,
       org_compartidos AS Organismos_Compartidos, mercado_total AS Mercado_Total_CLP
ORDER BY org_compartidos DESC LIMIT 20
"""

# ── Drill-down: entity biopsy ─────────────────────────────────────────────────

Q_VENDOR_DETAIL = """
MATCH (p:Proveedor {Nombre: $name})<-[:ADJUDICADA_A]-(oc:OrdenCompra_Item)-[:EMITIO]-(u:UnidadCompra)
RETURN u.UnidadCompra AS Organismo, oc.Fecha AS Fecha,
       oc.NombreEspecifico AS Descripción, oc.Monto AS Monto_CLP, oc.Modalidad AS Modalidad
ORDER BY oc.Monto DESC LIMIT 200
"""

Q_AGENCY_DETAIL = """
MATCH (u:UnidadCompra {UnidadCompra: $name})-[:EMITIO]->(oc:OrdenCompra_Item)-[:ADJUDICADA_A]->(p:Proveedor)
RETURN p.Nombre AS Proveedor, oc.Fecha AS Fecha,
       oc.NombreEspecifico AS Descripción, oc.Monto AS Monto_CLP, oc.Modalidad AS Modalidad
ORDER BY oc.Monto DESC LIMIT 200
"""

def _drill_down(entity: str, entity_col: str):
    """Shows a drill-down expander for any entity name clicked."""
    with st.expander(f"🔍 Ver detalle: {truncate(entity, 50)}"):
        is_vendor = entity_col in ("Proveedor", "Proveedor_A", "Proveedor_B", "Suspect_Vendor")
        q = Q_VENDOR_DETAIL if is_vendor else Q_AGENCY_DETAIL
        df = run_query(q, {"name": entity})
        if df.empty:
            st.info("Sin registros.")
            return
        df["Monto_CLP"] = pd.to_numeric(df["Monto_CLP"], errors="coerce")
        total = df["Monto_CLP"].sum()
        st.markdown(f"**{len(df)} transacciones** · Total: **{clp(total)}**")
        st.dataframe(df, width="stretch", height=300)


def _numeric(df: pd.DataFrame, *cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _tab_fragmentation():
    st.markdown(f"## {t('frag_title')}")
    st.markdown(t("frag_body"))

    # Pre-loaded top 20
    st.markdown(f"### {t('risk_top')}")
    with st.spinner(""):
        df_top = run_query(Q_FRAGMENTATION, {"umbral": 6_600_000})

    if not df_top.empty:
        df_top = _numeric(df_top, "Total_CLP", "N_Ordenes")
        df_top = df_top.head(20)
        st.markdown(t("frag_found").format(n=len(df_top)))

        v1, v2 = st.columns(2)
        with v1:
            st.markdown(f"#### {t('frag_chart1')}")
            top = (df_top.groupby("Organismo")["Total_CLP"].sum()
                   .sort_values(ascending=True).tail(12).reset_index())
            top["Organismo"] = top["Organismo"].apply(lambda x: truncate(x, 40))
            fig = px.bar(top, x="Total_CLP", y="Organismo", orientation="h",
                         color_discrete_sequence=["#B05C3B"])
            fig.update_layout(**CHART, xaxis=dict(tickformat="$,.0f"), yaxis_title="")
            st.plotly_chart(fig, width="stretch")
        with v2:
            st.markdown(f"#### {t('frag_chart2')}")
            fig2 = px.histogram(df_top, x="N_Ordenes", nbins=15,
                                color_discrete_sequence=["#1A1A1A"],
                                labels={"N_Ordenes": "Órdenes / Orders"})
            fig2.update_layout(**CHART, yaxis_title="Clusters")
            st.plotly_chart(fig2, width="stretch")

        # Highlights
        top3 = df_top.nlargest(3, "Total_CLP")
        for _, row in top3.iterrows():
            highlight(f"{truncate(row['Organismo'], 45)} → {truncate(row['Proveedor'], 35)} · {clp(row['Total_CLP'])} en mes {row['Mes']}")

        st.dataframe(df_top, width="stretch", height=320)

        # Drill-down
        rule()
        st.markdown(f"### Drill-down")
        entity = st.selectbox("Seleccionar organismo", df_top["Organismo"].unique(), key="dd_frag")
        if entity:
            _drill_down(entity, "Organismo")
    else:
        st.info(t("risk_no_data"))

    # Custom params
    rule()
    with st.expander(t("risk_adjust")):
        umbral = st.slider(t("frag_umbral"), 6_600_000, 50_000_000, 6_600_000, 500_000, key="s_frag")
        if st.button(t("risk_run"), key="r01"):
            df = run_query(Q_FRAGMENTATION, {"umbral": umbral})
            if not df.empty:
                df = _numeric(df, "Total_CLP", "N_Ordenes")
                st.markdown(t("frag_found").format(n=len(df)))
                st.dataframe(df, width="stretch", height=340)
                st.download_button(t("risk_export"), df.to_csv(index=False, sep=";").encode(), "frag.csv", "text/csv")
            else:
                st.info(t("risk_no_data"))


def _tab_capture():
    st.markdown(f"## {t('cap_title')}")
    st.markdown(t("cap_body"))

    st.markdown(f"### {t('risk_top')}")
    with st.spinner(""):
        df_top = run_query(Q_CAPTURE, {"pct": 40.0, "min_budget": 10_000_000.0})

    if not df_top.empty:
        df_top = _numeric(df_top, "Concentración_Pct", "Presupuesto_TD_CLP")
        df_top = df_top.head(20)
        st.markdown(t("cap_found").format(n=len(df_top), pct=40))

        v1, v2 = st.columns(2)
        with v1:
            st.markdown(f"#### {t('cap_chart1')}")
            top = df_top.sort_values("Concentración_Pct", ascending=True).tail(15).copy()
            top["Organismo"] = top["Organismo"].apply(lambda x: truncate(x, 38))
            fig = px.bar(top, x="Concentración_Pct", y="Organismo", orientation="h",
                         color="Concentración_Pct",
                         color_continuous_scale=["#F4F3EE", "#E8C97A", "#B05C3B"])
            fig.update_layout(**CHART, xaxis_title="% en un solo proveedor / in one vendor",
                              yaxis_title="", coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")
        with v2:
            st.markdown(f"#### {t('cap_chart2')}")
            fig2 = px.scatter(df_top, x="Presupuesto_TD_CLP", y="Concentración_Pct",
                              hover_data=["Organismo", "Proveedor"],
                              color_discrete_sequence=["#1A1A1A"])
            fig2.update_layout(**CHART, xaxis=dict(tickformat="$,.0f"))
            fig2.add_hline(y=40, line_dash="dot", line_color="#B05C3B", annotation_text="40%")
            st.plotly_chart(fig2, width="stretch")

        top3 = df_top.nlargest(3, "Concentración_Pct")
        for _, row in top3.iterrows():
            highlight(f"{truncate(row['Organismo'], 40)} → {truncate(row['Proveedor'], 35)} · {row['Concentración_Pct']}% concentración")

        st.dataframe(df_top, width="stretch", height=300)

        rule()
        st.markdown("### Drill-down")
        col_dd = st.selectbox("Seleccionar", ["Organismo", "Proveedor"], key="dd_cap_col")
        entity = st.selectbox("Entidad", df_top[col_dd].unique(), key="dd_cap")
        if entity:
            _drill_down(entity, col_dd)
    else:
        st.info(t("risk_no_data"))

    rule()
    with st.expander(t("risk_adjust")):
        c1, c2 = st.columns(2)
        with c1:
            pct = st.slider(t("cap_pct"), 30, 95, 40, key="s_cap_pct")
        with c2:
            min_budget = st.number_input(t("cap_budget"), value=10_000_000, step=1_000_000, key="s_cap_bgt")
        if st.button(t("risk_run"), key="r02"):
            df = run_query(Q_CAPTURE, {"pct": float(pct), "min_budget": float(min_budget)})
            if not df.empty:
                df = _numeric(df, "Concentración_Pct", "Presupuesto_TD_CLP")
                st.markdown(t("cap_found").format(n=len(df), pct=pct))
                st.dataframe(df, width="stretch", height=340)
                st.download_button(t("risk_export"), df.to_csv(index=False, sep=";").encode(), "capture.csv", "text/csv")
            else:
                st.info(t("risk_no_data"))


def _tab_pagerank():
    st.markdown(f"## {t('pr_title')}")
    st.markdown(t("pr_body"))

    st.markdown(f"### {t('risk_top')}")
    with st.spinner(""):
        df_top = run_query(Q_PAGERANK, {"n": 20})

    if not df_top.empty:
        df_top = _numeric(df_top, "Score")
        df_s = df_top.sort_values("Score", ascending=True).copy()
        df_s["Proveedor_s"] = df_s["Proveedor"].apply(lambda x: truncate(x, 42))

        fig = go.Figure(go.Bar(
            x=df_s["Score"], y=df_s["Proveedor_s"], orientation="h",
            marker=dict(color=df_s["Score"],
                        colorscale=[[0, "#EDEDEA"], [0.5, "#E8C97A"], [1, "#1A1A1A"]],
                        showscale=False)
        ))
        fig.update_layout(**CHART, xaxis_title="Influence score / Score de influencia",
                          yaxis_title="", height=max(380, 20 * 26))
        st.plotly_chart(fig, width="stretch")

        top3 = df_top.nlargest(3, "Score")
        for _, row in top3.iterrows():
            highlight(f"{truncate(row['Proveedor'], 50)} · PageRank {row['Score']:.4f}")

        st.dataframe(df_top, width="stretch")

        rule()
        st.markdown("### Drill-down")
        entity = st.selectbox("Seleccionar proveedor", df_top["Proveedor"].unique(), key="dd_pr")
        if entity:
            _drill_down(entity, "Proveedor")
    else:
        st.info(t("pr_no_scores"))

    rule()
    with st.expander(t("risk_adjust")):
        top_n = st.slider(t("pr_topn"), 5, 50, 20, key="s_pr")
        if st.button(t("risk_run"), key="r03"):
            df = run_query(Q_PAGERANK, {"n": top_n})
            if not df.empty:
                df = _numeric(df, "Score")
                st.dataframe(df.sort_values("Score", ascending=False), width="stretch")


def _tab_exclusivity():
    st.markdown(f"## {t('excl_title')}")
    st.markdown(t("excl_body"))

    st.markdown(f"### {t('risk_top')}")
    with st.spinner(""):
        df_top = run_query(Q_EXCLUSIVITY, {"min_rev": 5_000_000.0})

    if not df_top.empty:
        df_top = _numeric(df_top, "Ingresos_TD_CLP", "Ingresos_Totales_CLP")
        st.markdown(t("excl_found").format(n=len(df_top)))

        v1, v2 = st.columns(2)
        with v1:
            st.markdown(f"#### {t('excl_chart1')}")
            dp = df_top.copy()
            dp["Proveedor_s"] = dp["Proveedor"].apply(lambda x: truncate(x, 28))
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Total", x=dp["Proveedor_s"],
                                 y=dp["Ingresos_Totales_CLP"], marker_color="#EDEDEA"))
            fig.add_trace(go.Bar(name="TD exclusivo", x=dp["Proveedor_s"],
                                 y=dp["Ingresos_TD_CLP"], marker_color="#B05C3B"))
            fig.update_layout(**CHART, barmode="overlay", xaxis_tickangle=-35,
                              yaxis=dict(tickformat="$,.0f"), legend=dict(font=dict(size=9)))
            st.plotly_chart(fig, width="stretch")
        with v2:
            st.markdown(f"#### {t('excl_chart2')}")
            top_o = (df_top.groupby("Organismo_Principal")["Ingresos_TD_CLP"]
                     .sum().sort_values(ascending=True).reset_index())
            top_o["Organismo_Principal"] = top_o["Organismo_Principal"].apply(lambda x: truncate(x, 35))
            fig2 = px.bar(top_o, x="Ingresos_TD_CLP", y="Organismo_Principal",
                          orientation="h", color_discrete_sequence=["#4A7C8E"])
            fig2.update_layout(**CHART, xaxis=dict(tickformat="$,.0f"), yaxis_title="")
            st.plotly_chart(fig2, width="stretch")

        top3 = df_top.nlargest(3, "Ingresos_TD_CLP")
        for _, row in top3.iterrows():
            highlight(f"{truncate(row['Proveedor'], 40)} → {truncate(row['Organismo_Principal'], 35)} · {clp(row['Ingresos_TD_CLP'])}")

        st.dataframe(df_top, width="stretch", height=300)

        rule()
        st.markdown("### Drill-down")
        col_dd = st.selectbox("Seleccionar", ["Proveedor", "Organismo_Principal"], key="dd_excl_col")
        entity = st.selectbox("Entidad", df_top[col_dd].unique(), key="dd_excl")
        if entity:
            _drill_down(entity, col_dd)
    else:
        st.info(t("risk_no_data"))

    rule()
    with st.expander(t("risk_adjust")):
        min_rev = st.number_input(t("excl_min_rev"), value=5_000_000, step=1_000_000, key="s_excl")
        if st.button(t("risk_run"), key="r04"):
            df = run_query(Q_EXCLUSIVITY, {"min_rev": float(min_rev)})
            if not df.empty:
                df = _numeric(df, "Ingresos_TD_CLP", "Ingresos_Totales_CLP")
                st.markdown(t("excl_found").format(n=len(df)))
                st.dataframe(df, width="stretch", height=320)
                st.download_button(t("risk_export"), df.to_csv(index=False, sep=";").encode(), "excl.csv", "text/csv")
            else:
                st.info(t("risk_no_data"))


def _tab_bidding_rings():
    st.markdown(f"## {t('rings_title')}")
    st.markdown(t("rings_body"))

    st.markdown(f"### {t('risk_top')}")
    with st.spinner(""):
        df_top = run_query(Q_BIDDING_RINGS, {"min_monto": 5_000_000.0, "min_shared": 3})

    if not df_top.empty:
        df_top = _numeric(df_top, "Organismos_Compartidos", "Mercado_Total_CLP")
        df_top["Par"] = (df_top["Proveedor_A"].apply(lambda x: truncate(x, 22))
                         + " ↔ " + df_top["Proveedor_B"].apply(lambda x: truncate(x, 22)))
        st.markdown(t("rings_found").format(n=len(df_top)))

        v1, v2 = st.columns(2)
        with v1:
            st.markdown(f"#### {t('rings_chart1')}")
            fig = px.bar(df_top.sort_values("Organismos_Compartidos", ascending=True),
                         x="Organismos_Compartidos", y="Par", orientation="h",
                         color_discrete_sequence=["#1A1A1A"])
            fig.update_layout(**CHART, xaxis_title="Nº organismos compartidos / shared agencies", yaxis_title="")
            st.plotly_chart(fig, width="stretch")
        with v2:
            st.markdown(f"#### {t('rings_chart2')}")
            fig2 = px.bar(df_top.sort_values("Mercado_Total_CLP", ascending=True),
                          x="Mercado_Total_CLP", y="Par", orientation="h",
                          color_discrete_sequence=["#4A7C8E"])
            fig2.update_layout(**CHART, xaxis=dict(tickformat="$,.0f"), yaxis_title="")
            st.plotly_chart(fig2, width="stretch")

        top3 = df_top.nlargest(3, "Mercado_Total_CLP")
        for _, row in top3.iterrows():
            highlight(f"{row['Par']} · {clp(row['Mercado_Total_CLP'])} · {int(row['Organismos_Compartidos'])} organismos compartidos")

        st.dataframe(df_top.drop(columns=["Par"]), width="stretch", height=280)

        rule()
        st.markdown("### Drill-down")
        vendors = list(df_top["Proveedor_A"].unique()) + list(df_top["Proveedor_B"].unique())
        entity = st.selectbox("Seleccionar proveedor", sorted(set(vendors)), key="dd_rings")
        if entity:
            _drill_down(entity, "Proveedor_A")
    else:
        st.info(t("rings_no_data"))

    rule()
    with st.expander(t("risk_adjust")):
        c1, c2 = st.columns(2)
        with c1:
            min_monto = st.number_input(t("rings_amount"), value=5_000_000, step=500_000, key="s_rings_m")
        with c2:
            min_shared = st.slider(t("rings_shared"), 2, 10, 3, key="s_rings_s")
        if st.button(t("risk_run"), key="r05"):
            df = run_query(Q_BIDDING_RINGS, {"min_monto": float(min_monto), "min_shared": min_shared})
            if not df.empty:
                df = _numeric(df, "Organismos_Compartidos", "Mercado_Total_CLP")
                st.markdown(t("rings_found").format(n=len(df)))
                st.dataframe(df, width="stretch", height=300)
                st.download_button(t("risk_export"), df.to_csv(index=False, sep=";").encode(), "rings.csv", "text/csv")
            else:
                st.info(t("rings_no_data"))


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown(f"# {t('risk_title')}")
    st.markdown(t("risk_subtitle"))
    rule()

    tabs = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5")])
    with tabs[0]: _tab_fragmentation()
    with tabs[1]: _tab_capture()
    with tabs[2]: _tab_pagerank()
    with tabs[3]: _tab_exclusivity()
    with tabs[4]: _tab_bidding_rings()
