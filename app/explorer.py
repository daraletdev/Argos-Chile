import streamlit as st
import pandas as pd
import plotly.express as px
from db import run_query
from fmt import clp, truncate
from styles import rule, kpi, CHART, PALETTE
from i18n import t

VENDOR_QUERY = """
MATCH (p:Proveedor {Nombre: $name})<-[:ADJUDICADA_A]-(oc:OrdenCompra_Item)-[:EMITIO]-(u:UnidadCompra)
RETURN u.UnidadCompra AS Organismo, oc.Fecha AS Fecha,
       oc.NombreEspecifico AS Descripción, oc.Monto AS Monto_CLP,
       oc.Modalidad AS Modalidad, oc.CodigoUnico AS ID
ORDER BY oc.Monto DESC
"""

AGENCY_QUERY = """
MATCH (u:UnidadCompra {UnidadCompra: $name})-[:EMITIO]->(oc:OrdenCompra_Item)-[:ADJUDICADA_A]->(p:Proveedor)
RETURN p.Nombre AS Proveedor, oc.Fecha AS Fecha,
       oc.NombreEspecifico AS Descripción, oc.Monto AS Monto_CLP,
       oc.Modalidad AS Modalidad, oc.CodigoUnico AS ID
ORDER BY oc.Monto DESC
"""

def _kpis(df: pd.DataFrame):
    total   = pd.to_numeric(df["Monto_CLP"], errors="coerce").sum()
    n_trans = len(df)
    n_cp    = df.iloc[:, 0].nunique()
    top_mod = df["Modalidad"].value_counts().idxmax() if "Modalidad" in df.columns else "—"
    k1, k2, k3, k4 = st.columns(4)
    for col, label, val in [
        (k1, t("exp_kpi_total"), clp(total)),
        (k2, t("exp_kpi_trans"), f"{n_trans:,}"),
        (k3, t("exp_kpi_cp"),    f"{n_cp:,}"),
        (k4, t("exp_kpi_modal"), top_mod),
    ]:
        with col:
            kpi(label, val)

def _charts(df: pd.DataFrame, entity_type: str):
    df["Monto_CLP"] = pd.to_numeric(df["Monto_CLP"], errors="coerce")
    v1, v2 = st.columns(2)

    with v1:
        st.markdown(f"### {t('exp_modal_dist')}")
        md = df.groupby("Modalidad")["Monto_CLP"].sum().reset_index()
        md.columns = ["Modalidad", "Total"]
        fig = px.pie(md, values="Total", names="Modalidad",
                     color_discrete_sequence=PALETTE, hole=0.45)
        fig.update_layout(**CHART, showlegend=True)
        fig.update_traces(textinfo="percent+label", textfont_size=11)
        st.plotly_chart(fig, width="stretch")

    with v2:
        st.markdown(f"### {t('exp_top_cp')}")
        cp_col = "Organismo" if entity_type == t("exp_vendor") else "Proveedor"
        if cp_col in df.columns:
            top = (df.groupby(cp_col)["Monto_CLP"].sum()
                   .sort_values(ascending=True).tail(10).reset_index())
            top.columns = ["Entidad", "Total"]
            top["Entidad"] = top["Entidad"].apply(lambda x: truncate(x, 38))
            fig2 = px.bar(top, x="Total", y="Entidad", orientation="h",
                          color_discrete_sequence=["#1A1A1A"])
            fig2.update_layout(**CHART, xaxis=dict(tickformat="$,.0f"), yaxis_title="")
            st.plotly_chart(fig2, width="stretch")

    if "Fecha" in df.columns and df["Fecha"].notna().any():
        st.markdown(f"### {t('exp_monthly')}")
        try:
            df["_mes"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.to_period("M").astype(str)
            td = df.groupby("_mes")["Monto_CLP"].sum().reset_index()
            fig3 = px.area(td, x="_mes", y="Monto_CLP", color_discrete_sequence=["#1A1A1A"])
            fig3.update_layout(**CHART, xaxis_title="", yaxis=dict(tickformat="$,.0f"))
            fig3.update_traces(fillcolor="rgba(26,26,26,0.08)", line_color="#1A1A1A")
            st.plotly_chart(fig3, width="stretch")
        except Exception:
            pass

def _table(df: pd.DataFrame):
    rule()
    st.markdown(f"### {t('exp_detail')}")
    f1, f2 = st.columns(2)
    with f1:
        mods = [t("exp_all")] + sorted(df["Modalidad"].dropna().unique().tolist())
        mod_f = st.selectbox(t("exp_filter_mod"), mods)
    with f2:
        sort_by = st.selectbox(t("exp_sort"), ["Monto_CLP", "Fecha"] if "Fecha" in df.columns else ["Monto_CLP"])

    df_show = df.copy().drop(columns=["_mes"], errors="ignore")
    if mod_f != t("exp_all"):
        df_show = df_show[df_show["Modalidad"] == mod_f]
    if sort_by in df_show.columns:
        df_show = df_show.sort_values(sort_by, ascending=False)

    st.dataframe(df_show, width="stretch", height=420)
    st.download_button(
        t("exp_export"),
        df_show.to_csv(index=False, sep=";").encode("utf-8"),
        "resultados.csv", "text/csv"
    )

def render():
    st.markdown(f"# {t('exp_title')}")
    st.markdown(t("exp_subtitle"))
    rule()

    col_inp, col_type = st.columns([3, 1])
    with col_inp:
        entity = st.text_input(t("exp_input"), placeholder=t("exp_placeholder"))
    with col_type:
        entity_type = st.selectbox(t("exp_type"), [t("exp_vendor"), t("exp_agency")])

    if not entity:
        return

    query = VENDOR_QUERY if entity_type == t("exp_vendor") else AGENCY_QUERY
    with st.spinner(""):
        df = run_query(query, {"name": entity})

    if df.empty:
        st.info(t("exp_not_found").format(entity))
        return

    _kpis(df)
    rule()
    _charts(df, entity_type)
    _table(df)
