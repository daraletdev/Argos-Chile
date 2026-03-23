import re
import collections
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

ORDER_LIMIT  = 6_600_000
TENDER_LIMIT = 66_000_000

SHORT_MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}
LONG_MONTHS = {
    1: "enero",      2: "febrero",   3: "marzo",      4: "abril",
    5: "mayo",       6: "junio",     7: "julio",       8: "agosto",
    9: "septiembre", 10: "octubre",  11: "noviembre",  12: "diciembre",
}

EXPORT_COLS = [
    "agency", "vendor", "month_name", "month", "order_count", "total_clp",
    "threshold_multiplier", "min_amount", "max_amount", "avg_amount",
    "orders_over_limit", "pct_identical_amount", "pct_identical_desc",
    "base_quote", "unique_quotes", "n_months", "month_list",
    "annual_total", "evidence_score", "chronicity_score", "scale_score",
    "total_score", "risk_level", "legal_basis", "description_sample",
]

RISK_ORDER = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}

REPORT_SECTIONS = [
    ("CRÍTICO", "Evidencia forense sólida + cronicidad + escala. Prioridad máxima."),
    ("ALTO",    "Dos o más dimensiones con puntuación alta."),
    ("MEDIO",   "Una dimensión fuerte. Requiere revisión documental."),
    ("BAJO",    "Volumen supera el umbral legal. Se incluyen por completitud."),
]


# ── Indicators ────────────────────────────────────────────────────────────────

def _compute_indicators(row) -> pd.Series:
    amounts: list[float] = [float(m) for m in row["amounts"] if m is not None]
    descs:   list[str]   = [str(d)   for d in row["descriptions"] if d is not None]
    ids:     list[str]   = [str(i)   for i in row["ids"] if i is not None]
    n = len(amounts)

    if n == 0:
        return pd.Series({
            "min_amount": None, "max_amount": None, "avg_amount": None,
            "orders_over_limit": 0, "pct_identical_amount": 0.0,
            "pct_identical_desc": 0.0, "base_quote": "—",
            "unique_quotes": 0, "description_sample": "—",
        })

    amount_counts = collections.Counter(amounts).most_common(1)
    amount_top    = amount_counts[0][1] if amount_counts else 0

    desc_counts = collections.Counter(descs).most_common(1)
    desc_top    = desc_counts[0][1] if desc_counts else 0

    bases: list[str] = []
    for i in ids:
        if m := re.match(r"(\d+-\d+-AG25)", i):
            bases.append(m.group(1))

    base_counts = collections.Counter(bases).most_common(1)
    base_quote  = base_counts[0][0] if base_counts else "—"

    return pd.Series({
        "min_amount":           min(amounts),
        "max_amount":           max(amounts),
        "avg_amount":           sum(amounts) / n,
        "orders_over_limit":    sum(1 for a in amounts if a > ORDER_LIMIT),
        "pct_identical_amount": round(amount_top / n * 100, 1),
        "pct_identical_desc":   round(desc_top / n * 100, 1),
        "base_quote":           base_quote,
        "unique_quotes":        len(set(bases)),
        "description_sample":   descs[0][:120] if descs else "—",
    })


# ── Scoring ───────────────────────────────────────────────────────────────────

def _evidence_score(row) -> int:
    if row["pct_identical_amount"] > 80 and row["pct_identical_desc"] > 80:
        return 3
    if row["unique_quotes"] == 1:
        return 3
    if row["pct_identical_amount"] > 80 or row["pct_identical_desc"] > 80:
        return 2
    return 1


def _risk_level(total: int) -> str:
    if total >= 7: return "CRÍTICO"
    if total >= 6: return "ALTO"
    if total >= 4: return "MEDIO"
    return "BAJO"


def _legal_basis(row) -> str:
    parts: list[str] = []

    if row["evidence_score"] == 3:
        n = row["unique_quotes"]
        label = "cotización" if n == 1 else "cotizaciones"
        parts.append(
            f"{row['pct_identical_amount']:.0f}% de las órdenes tienen monto idéntico y "
            f"{row['pct_identical_desc']:.0f}% descripción idéntica, "
            f"derivadas de {n} {label} base."
        )
    elif row["evidence_score"] == 2:
        parts.append("Montos o descripciones parcialmente repetitivos.")
    else:
        parts.append("Variedad en montos y descripciones — compras diversas posibles.")

    if row["chronicity_score"] == 3:
        months = ", ".join(row["month_list"])
        parts.append(
            f"Patrón sistemático en {row['n_months']} meses ({months}). "
            f"La recurrencia elimina el argumento de imprevisibilidad "
            f"(Dictamen CGR, Municipalidad de La Cisterna)."
        )
    elif row["chronicity_score"] == 2:
        parts.append(f"Patrón recurrente en {row['n_months']} meses.")

    if row["scale_score"] >= 2:
        parts.append(
            f"Total acumulado: ${row['total_clp']/1e6:,.0f} M CLP "
            f"({row['threshold_multiplier']:.1f}x el umbral de licitación obligatoria)."
        )

    return " ".join(parts)


# ── Main processing ───────────────────────────────────────────────────────────

def process(df_raw: pd.DataFrame) -> pd.DataFrame:
    ind = df_raw.apply(_compute_indicators, axis=1)
    df  = pd.concat([df_raw.drop(columns=["amounts", "descriptions", "ids"]), ind], axis=1)

    df["threshold_multiplier"] = (df["total_clp"] / TENDER_LIMIT).round(1)
    df["month_name"]           = df["month"].map(SHORT_MONTHS)

    chronic = (
        df.groupby(["agency", "vendor"])
        .agg(
            n_months    = ("month",      "count"),
            month_list  = ("month_name", lambda x: sorted(set(x))),
            annual_total= ("total_clp",  "sum"),
        )
        .reset_index()
    )
    df = df.merge(chronic, on=["agency", "vendor"], how="left")

    df["evidence_score"]   = df.apply(_evidence_score, axis=1)
    df["chronicity_score"] = df["n_months"].apply(lambda n: 3 if n >= 6 else 2 if n >= 3 else 1)
    df["scale_score"]      = df["threshold_multiplier"].apply(lambda m: 3 if m >= 50 else 2 if m >= 10 else 1)
    df["total_score"]      = df["evidence_score"] + df["chronicity_score"] + df["scale_score"]
    df["risk_level"]       = df["total_score"].apply(_risk_level)
    df["legal_basis"]      = df.apply(_legal_basis, axis=1)

    df["_ord"] = df["risk_level"].map(RISK_ORDER)
    df = (df.sort_values(["_ord", "total_score", "total_clp"], ascending=[True, False, False])
            .drop(columns="_ord")
            .reset_index(drop=True))
    return df


# ── Export ────────────────────────────────────────────────────────────────────

def export_csv(df: pd.DataFrame, path: str) -> None:
    df[EXPORT_COLS].to_csv(path, index=False, sep=";", encoding="utf-8-sig")


def export_markdown(df: pd.DataFrame, path: str) -> None:
    template_dir = Path(__file__).parent / "templates"
    env      = Environment(loader=FileSystemLoader(str(template_dir)),
                           trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("reporte.md.j2")

    def _row_context(r) -> dict:
        pct        = r["avg_amount"] / ORDER_LIMIT * 100 if r["avg_amount"] else 0
        month_list = r["month_list"] if isinstance(r["month_list"], list) else [r["month_list"]]
        return {
            "organismo":       r["agency"],
            "proveedor":       r["vendor"],
            "mes_nombre":      LONG_MONTHS.get(int(r["month"]), str(r["month"])),
            "n_ordenes":       int(r["order_count"]),
            "total_mes":       f"{r['total_clp']/1e6:,.1f}",
            "total_anual":     f"{r['annual_total']/1e9:.2f}",
            "multiplicador":   r["threshold_multiplier"],
            "monto_min":       f"{r['min_amount']/1e6:.2f}",
            "monto_max":       f"{r['max_amount']/1e6:.2f}",
            "pct_limite":      f"{pct:.0f}",
            "pct_monto":       r["pct_identical_amount"],
            "pct_desc":        r["pct_identical_desc"],
            "cotizacion_base": r["base_quote"],
            "n_cotizaciones":  int(r["unique_quotes"]),
            "n_meses":         int(r["n_months"]),
            "meses_lista":     ", ".join(month_list),
            "score_e":         int(r["evidence_score"]),
            "score_c":         int(r["chronicity_score"]),
            "score_s":         int(r["scale_score"]),
            "nivel":           r["risk_level"],
            "descripcion":     r["description_sample"],
            "argumento":       r["legal_basis"],
        }

    sections = [
        (name, [_row_context(r) for _, r in df[df["risk_level"] == name].iterrows()], desc)
        for name, desc in REPORT_SECTIONS
        if len(df[df["risk_level"] == name])
    ]

    content = template.render(
        fecha         = datetime.now().strftime("%d/%m/%Y"),
        total         = f"{len(df):,}",
        n_critico     = len(df[df["risk_level"] == "CRÍTICO"]),
        n_alto        = len(df[df["risk_level"] == "ALTO"]),
        n_medio       = len(df[df["risk_level"] == "MEDIO"]),
        n_bajo        = len(df[df["risk_level"] == "BAJO"]),
        monto_total   = f"{df['total_clp'].sum()/1e9:.1f}",
        mult_promedio = f"{df['threshold_multiplier'].mean():.1f}",
        secciones     = sections,
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)