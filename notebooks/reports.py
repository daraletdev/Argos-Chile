"""
Generador de reportes de fraccionamiento.
Toma el DataFrame procesado y exporta CSV + Markdown.
"""

import os
import re
from collections import Counter
from datetime import datetime

import pandas as pd

LIMITE_ORDEN   = 6_600_000
LIMITE_LICITAR = 66_000_000

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def calcular_indicadores(row):
    montos = [float(m) for m in row["Montos"] if m is not None]
    descs  = [str(d) for d in row["Descripciones"] if d is not None]
    ids    = [str(i) for i in row["IDs"] if i is not None]
    n = len(montos)

    if n == 0:
        return pd.Series({
            "Monto_Min": None, "Monto_Max": None, "Monto_Medio": None,
            "Ordenes_Sobre_Limite": 0, "Pct_Monto_Identico": 0,
            "Pct_Desc_Identica": 0, "Cotizacion_Base": "—",
            "Cotizaciones_Unicas": 0, "Desc_Muestra": "—",
        })

    monto_top = Counter(montos).most_common(1)[0][1]
    desc_top  = Counter(descs).most_common(1)[0][1] if descs else 0

    bases = [
        re.match(r"(\d+-\d+-AG25)", i).group(1)
        for i in ids if re.match(r"(\d+-\d+-AG25)", i)
    ]
    cot_unicas = len(set(bases))
    cot_base   = Counter(bases).most_common(1)[0][0] if bases else "—"

    return pd.Series({
        "Monto_Min":            min(montos),
        "Monto_Max":            max(montos),
        "Monto_Medio":          sum(montos) / n,
        "Ordenes_Sobre_Limite": sum(1 for m in montos if m > LIMITE_ORDEN),
        "Pct_Monto_Identico":   round(monto_top / n * 100, 1),
        "Pct_Desc_Identica":    round(desc_top / n * 100, 1),
        "Cotizacion_Base":      cot_base,
        "Cotizaciones_Unicas":  cot_unicas,
        "Desc_Muestra":         descs[0][:120] if descs else "—",
    })


def calcular_cronicidad(df):
    cronic = (
        df.groupby(["Organismo", "Proveedor"])
        .agg(
            N_Meses=("Mes", "count"),
            Meses_Lista=("Mes_Nombre", lambda x: sorted(set(x))),
            Total_Anual=("Total_CLP", "sum"),
        )
        .reset_index()
    )
    return df.merge(cronic, on=["Organismo", "Proveedor"], how="left")


def score_evidencia(row):
    if row["Pct_Monto_Identico"] > 80 and row["Pct_Desc_Identica"] > 80:
        return 3
    if row["Cotizaciones_Unicas"] == 1:
        return 3
    if row["Pct_Monto_Identico"] > 80 or row["Pct_Desc_Identica"] > 80:
        return 2
    return 1


def score_cronicidad(n):
    if n >= 6: return 3
    if n >= 3: return 2
    return 1


def score_escala(mult):
    if mult >= 50: return 3
    if mult >= 10: return 2
    return 1


def clasificar(row):
    s = row["Score_Total"]
    if s >= 7: return "CRÍTICO"
    if s >= 6: return "ALTO"
    if s >= 4: return "MEDIO"
    return "BAJO"


def argumento_legal(row):
    partes = []

    if row["Score_Evidencia"] == 3:
        partes.append(
            f"{row['Pct_Monto_Identico']:.0f}% de las órdenes tienen monto idéntico y "
            f"{row['Pct_Desc_Identica']:.0f}% descripción idéntica, "
            f"derivadas de {row['Cotizaciones_Unicas']} "
            f"{'cotización' if row['Cotizaciones_Unicas'] == 1 else 'cotizaciones'} base."
        )
    elif row["Score_Evidencia"] == 2:
        partes.append("Montos o descripciones parcialmente repetitivos.")
    else:
        partes.append("Variedad en montos y descripciones — compras diversas posibles.")

    if row["Score_Cronicidad"] == 3:
        meses = ", ".join(row["Meses_Lista"])
        partes.append(
            f"Patrón sistemático en {row['N_Meses']} meses ({meses}). "
            f"La recurrencia elimina el argumento de imprevisibilidad "
            f"(Dictamen CGR, Municipalidad de La Cisterna)."
        )
    elif row["Score_Cronicidad"] == 2:
        partes.append(f"Patrón recurrente en {row['N_Meses']} meses.")

    if row["Score_Escala"] >= 2:
        partes.append(
            f"Total acumulado: ${row['Total_CLP']/1e6:,.0f} M CLP "
            f"({row['Multiplicador']:.1f}x el umbral de licitación obligatoria)."
        )

    return " ".join(partes)


def procesar(df_raw):
    ind = df_raw.apply(calcular_indicadores, axis=1)
    df  = pd.concat([df_raw.drop(columns=["Montos", "Descripciones", "IDs"]), ind], axis=1)

    df["Multiplicador"] = (df["Total_CLP"] / LIMITE_LICITAR).round(1)
    df["Mes_Nombre"]    = df["Mes"].map({
        1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun",
        7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic",
    })

    df = calcular_cronicidad(df)

    df["Score_Evidencia"]  = df.apply(score_evidencia, axis=1)
    df["Score_Cronicidad"] = df["N_Meses"].apply(score_cronicidad)
    df["Score_Escala"]     = df["Multiplicador"].apply(score_escala)
    df["Score_Total"]      = df["Score_Evidencia"] + df["Score_Cronicidad"] + df["Score_Escala"]
    df["Nivel_Final"]      = df.apply(clasificar, axis=1)
    df["Argumento_Legal"]  = df.apply(argumento_legal, axis=1)

    orden = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    df["_ord"] = df["Nivel_Final"].map(orden)
    df = df.sort_values(["_ord", "Score_Total", "Total_CLP"],
                        ascending=[True, False, False]).drop(columns="_ord")
    return df


def exportar_csv(df, ruta):
    cols = [
        "Organismo", "Proveedor", "Mes_Nombre", "Mes", "N_Ordenes", "Total_CLP",
        "Multiplicador", "Monto_Min", "Monto_Max", "Monto_Medio",
        "Ordenes_Sobre_Limite", "Pct_Monto_Identico", "Pct_Desc_Identica",
        "Cotizacion_Base", "Cotizaciones_Unicas", "N_Meses", "Meses_Lista",
        "Total_Anual", "Score_Evidencia", "Score_Cronicidad", "Score_Escala",
        "Score_Total", "Nivel_Final", "Argumento_Legal", "Desc_Muestra",
    ]
    df[cols].to_csv(ruta, index=False, sep=";", encoding="utf-8-sig")


def _ficha(r, idx):
    pct = r["Monto_Medio"] / LIMITE_ORDEN * 100 if r["Monto_Medio"] else 0
    meses_str = (", ".join(r["Meses_Lista"])
                 if isinstance(r["Meses_Lista"], list) else r["Meses_Lista"])
    return "\n".join([
        f"### {idx}. {r['Organismo']}",
        "",
        "| | |", "|---|---|",
        f"| Proveedor | `{r['Proveedor']}` |",
        f"| Mes | {MESES_ES.get(int(r['Mes']), str(r['Mes']))} 2025 |",
        f"| Órdenes | **{int(r['N_Ordenes'])}** |",
        f"| Total acumulado | **${r['Total_CLP']/1e6:,.1f} M CLP** |",
        f"| Total anual (par) | ${r['Total_Anual']/1e9:.2f} B CLP |",
        f"| Multiplicador | **{r['Multiplicador']:.1f}x** el umbral de licitación |",
        f"| Rango por orden | ${r['Monto_Min']/1e6:.2f} M – ${r['Monto_Max']/1e6:.2f} M |",
        f"| Monto unitario / límite AG | {pct:.0f}% |",
        f"| % monto idéntico | {r['Pct_Monto_Identico']:.0f}% |",
        f"| % descripción idéntica | {r['Pct_Desc_Identica']:.0f}% |",
        f"| Cotización base | `{r['Cotizacion_Base']}` "
        f"({int(r['Cotizaciones_Unicas'])} "
        f"{'cotización' if r['Cotizaciones_Unicas'] == 1 else 'cotizaciones'}) |",
        f"| Meses con fraccionamiento | {int(r['N_Meses'])} ({meses_str}) |",
        f"| Puntaje E / C / S | {int(r['Score_Evidencia'])} / "
        f"{int(r['Score_Cronicidad'])} / {int(r['Score_Escala'])} |",
        f"| Nivel | **{r['Nivel_Final']}** |",
        "",
        f"**Descripción:** _{r['Desc_Muestra']}_",
        "",
        f"> {r['Argumento_Legal']}",
        "",
        "---",
        "",
    ])


def exportar_markdown(df, ruta):
    critico = df[df["Nivel_Final"] == "CRÍTICO"]
    alto    = df[df["Nivel_Final"] == "ALTO"]
    medio   = df[df["Nivel_Final"] == "MEDIO"]
    bajo    = df[df["Nivel_Final"] == "BAJO"]

    doc = [
        "# Reporte Forense — Fraccionamiento en Compras Públicas Chile 2025",
        f"**Argos · {datetime.now().strftime('%d/%m/%Y')}**",
        "",
        "> Los hallazgos son indicios estadísticos basados en patrones objetivos de datos públicos.",
        "> No constituyen prueba de fraude ni determinación legal.",
        "> Cada caso requiere verificación documental independiente.",
        "",
        "**Fundamento legal:**",
        "- DS 250 art. 13 · DS 661 art. 16 (diciembre 2024)",
        "- Dictamen CGR, Municipalidad de La Cisterna",
        "- Navarrete Millón, M. (2024). *Fragmentación en compras públicas*. ISBN 978-956-405-179-6",
        "- Sanciones: 10 a 100 UTM + responsabilidad administrativa",
        "",
        "---", "",
        "## Resumen", "",
        "| | |", "|---|---|",
        f"| Umbral de análisis | 1.000 UTM = $66 M CLP |",
        f"| Total casos | {len(df):,} |",
        f"| CRÍTICO | {len(critico):,} |",
        f"| ALTO | {len(alto):,} |",
        f"| MEDIO | {len(medio):,} |",
        f"| BAJO | {len(bajo):,} |",
        f"| Monto total expuesto | ${df['Total_CLP'].sum()/1e9:.1f} B CLP |",
        f"| Multiplicador promedio | {df['Multiplicador'].mean():.1f}x |",
        "", "---", "",
    ]

    niveles = [
        ("CRÍTICO", critico, "Evidencia forense + cronicidad + escala. Prioridad máxima."),
        ("ALTO",    alto,    "Dos o más dimensiones con puntuación alta."),
        ("MEDIO",   medio,   "Una dimensión fuerte. Requiere revisión documental."),
        ("BAJO",    bajo,    "Volumen supera el umbral legal. Se incluyen por completitud."),
    ]

    for nombre, subset, desc in niveles:
        if len(subset):
            doc += [f"## {nombre}", "", desc, ""]
            for i, (_, r) in enumerate(subset.iterrows(), 1):
                doc.append(_ficha(r, i))

    doc += [
        "---", "## Metodología", "",
        "**Fuente:** Mercado Público Chile — órdenes de compra 2025  ",
        "**Base de datos:** Neo4j Property Graph (1.7M nodos)  ",
        "**Criterio de inclusión:** Par organismo–proveedor con total mensual ≥ 1.000 UTM vía AG  ",
        "",
        "**Sistema de puntuación (1–3 por dimensión):**  ",
        "- Evidencia forense: % monto idéntico, % descripción idéntica, cotización base única  ",
        "- Cronicidad: meses del año con fraccionamiento detectado  ",
        "- Escala: multiplicador sobre el umbral de licitación  ",
        "",
        "**Limitaciones:**  ",
        "- `NombreEspecifico` puede estar truncado en la fuente original  ",
        "- No se evalúa si el bien era técnicamente indivisible  ",
        "- La clasificación no considera urgencias operacionales declaradas  ",
    ]

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(doc))
