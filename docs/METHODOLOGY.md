[🇨🇱 Versión en español](METHODOLOGY_ES.md)

# Argos — Technical Documentation and Methodology

---

## Project Structure

```
argos/
├── scripts/
│   ├── 00_download_bronze.py      raw data download
│   ├── 01_process_silver.py       cleaning and normalization
│   ├── 02_bulk_ingestion.py       load into Neo4j
│   ├── 03_create_projection.py    GDS projection
│   └── 04_run_analytics.py        algorithm execution
├── src/argos/
│   ├── etl/
│   │   ├── crawler.py             HTTP client for Mercado Público
│   │   └── cleaner.py             DataSanitizer — forensic cleaning
│   └── analytics/
│       └── risk_engine.py         risk detection engines
├── notebooks/
│   ├── 01_eda.ipynb               data exploration
│   ├── 02_risk_analysis.ipynb     fragmentation analysis
│   ├── 03_deep_case_investigation.ipynb   automated case investigation
│   └── 04_visualizaciones.ipynb   charts and report export
├── docs/
│   ├── reporte_fraccionamiento_final.md   complete report (generated)
│   └── fraccionamiento_blindado.csv       complete data (generated)
├── docker-compose.yml
└── pyproject.toml
```

---

## Data Pipeline

### Bronze Layer — Raw Data

`scripts/00_download_bronze.py` downloads monthly ZIP files from the Mercado Público blob storage:

```
https://transparenciachc.blob.core.windows.net/oc-da/2025-{month}.zip
```

Each file contains the accepted purchase orders for the month in CSV format with `;` separator and `latin-1` encoding.

### Silver Layer — Clean Data

`src/argos/etl/cleaner.py` applies the following transformations:

- Selection of 17 strategic columns for the graph model.
- Filtering to valid states: Accepted, Received, In process, Sent to supplier.
- Normalization of amounts in Chilean format (`1.234.567,89` → `1234567.89`).
- Elimination of transactions with zero or negative amounts.
- Text sanitization for Neo4j (quotes, line breaks, semicolons).
- Normalization of `SupplierCode` — converting floats like `25638.0` to integers `25638` to avoid duplicate nodes in the graph.

### Gold Layer — Neo4j Graph

`scripts/02_bulk_ingestion.py` builds the graph using APOC batch:

```cypher
MERGE (u:PurchasingUnit {UnitRut: row.RutUnidadCompra})
MERGE (p:Supplier {SupplierCode: toString(toInteger(toFloat(row.CodigoProveedor)))})
MERGE (pr:Product {GenericCategory: row.NombreroductoGenerico})
MERGE (oc:PurchaseOrder_Item {UniqueCode: row.Codigo + '-' + row.IDItem})
MERGE (u)-[:ISSUED]->(oc)
MERGE (oc)-[:AWARDED_TO]->(p)
MERGE (oc)-[:CLASSIFIED_AS]->(pr)
```

**Uniqueness Constraints:**
- `PurchasingUnit.UnitRut`
- `Supplier.SupplierCode`
- `Product.GenericCategory`
- `PurchaseOrder_Item.UniqueCode`

**Graph Scale (2025):**

| Node | Total |
|------|-------|
| PurchaseOrder_Item | 1,649,920 |
| Product | 66,737 |
| Supplier | 49,020 |
| PurchasingUnit | 1,976 |

---

## Detection Methodology

### Operational Definition of Fragmentation

An organization–supplier pair in a given month is considered a fragmentation case when:

1. The modality of all orders is `AG` (Agile Purchase).
2. The number of orders in the month is greater than 1.
3. The accumulated amount for the month exceeds **1,000 UTM ($66M CLP)** — the threshold above which the law requires a public tender.

The 1,000 UTM threshold (not 100 UTM) is deliberate: the analysis looks for cases where the State had a **legal obligation to tender** and did not, not simply cases where Agile Purchase was used.

### Case Indicators

For each detected pair, the following indicators are calculated from individual orders:

| Indicator | Description | Relevance |
|-----------|-------------|------------|
| `Pct_Identical_Amount` | % of orders with the exact same amount | Amounts identical to the cent are evidence of batch issuance |
| `Pct_Identical_Desc` | % of orders with the same description | Same good or service artificially split |
| `Base_Quote` | Source quote code | A single quote split into N items is the most direct evidence |
| `Unique_Quotes` | Number of distinct quotes | 1 = a single fragmented purchase |
| `Mean_Amount / ORDER_LIMIT` | Unit amount as % of the AG limit | Values close to 100% indicate deliberate adjustment |

### Scoring System

Each case receives between 1 and 3 points across three independent dimensions:

**Dimension A — Forensic Evidence:**
- 3 pts: `Pct_Identical_Amount > 80%` AND `Pct_Identical_Desc > 80%`, or `Unique_Quotes == 1`
- 2 pts: one of the two criteria exceeds 80%
- 1 pt: variety in amounts and descriptions

**Dimension B — Chronicity:**
- 3 pts: the same pair appears in 6 or more months of the year
- 2 pts: 3 to 5 months
- 1 pt: 1 to 2 months

Chronicity is heavily weighted because it eliminates the argument of total amount unpredictability. An organization fragmenting the same contract for 7 consecutive months cannot argue it did not anticipate the total would exceed the tender threshold. This follows the Comptroller General's (CGR) ruling in the Municipality of La Cisterna case.

**Dimension C — Scale:**
- 3 pts: multiplier ≥ 50x the threshold
- 2 pts: 10x–50x
- 1 pt: <10x

**Final Classification:**

| Level | Score | Criterion |
|-------|-----------|---------|
| CRITICAL | ≥ 7 | All dimensions high simultaneously |
| HIGH | ≥ 6 | Two dimensions with high scores |
| MEDIUM | ≥ 4 | One strong dimension |
| LOW | < 4 | Volume exceeds legal threshold — included for completeness |

---

## Known Limitations

**On Data:**
- The `SpecificName` field of orders may be truncated in the original source, affecting the `Pct_Identical_Desc` calculation.
- `SupplierCode` may appear as an integer or float across different months — corrected in the cleaner, but earlier graph versions may have duplicate nodes.

**On Methodology:**
- The analysis does not evaluate if the good or service was technically indivisible by nature.
- It does not consider operational context or formally declared emergencies.
- Cases classified as LOW may include various legitimate purchases from a regular supplier where the accumulated volume exceeds the threshold without the items being equivalent.
- Official intent is not determinable through transaction data alone.

**On Legal Scope:**
- Findings are statistical indications, not proof of fraud.
- The determination of illegality corresponds to the Comptroller General or competent prosecutors.
- The analysis does not cover public tender fraud, irregular direct contracting, or other types of public procurement irregularities.

---

## Legal Framework and References

**Regulations:**
- Law 19.886 on Grounds for Administrative Contracts for Supply and Service Provision.
- DS 250 art. 13 — definition of fragmentation and express prohibition.
- DS 661 art. 16 (December 2024) — new regulation, reinforcing the prohibition.

**Jurisprudence:**
- CGR Ruling, Municipality of La Cisterna case — rejected the independent cost center argument when the total exceeds 1,000 UTM in purchases from the same supplier.

**Bibliography:**
- Navarrete Millón, M. (2024). *Fragmentación en compras públicas*. ISBN 978-956-405-179-6. ChileCompra / Pontificia Universidad Católica de Chile. The author, head of Transparency at ChileCompra, defines fragmentation as "the bad practice of subdividing the purchase of a set of goods or services required by a public organization into repetitive processes of lower value with the aim of eluding the use of procurement procedures subject to greater controls and administrative requirements." He also recognizes that automated monitoring is an unresolved need of the system.

**Data Source:**
- Mercado Público Chile — 2025 purchase order open data.
- URL: `https://transparenciachc.blob.core.windows.net/oc-da/`

---

## Reproducibility

To exactly reproduce the results of this analysis:

```bash
# Verify that the graph has no duplicate SupplierCode nodes
# (should return 0 after a clean ingestion)
MATCH (p1:Supplier), (p2:Supplier)
WHERE toInteger(toFloat(toString(p1.SupplierCode))) =
      toInteger(toFloat(toString(p2.SupplierCode)))
  AND elementId(p1) < elementId(p2)
RETURN count(*) AS duplicates
```

```bash
# Verify graph scale
MATCH (n) RETURN labels(n)[0] AS Type, count(n) AS Total ORDER BY Total DESC
```

Notebooks are designed to be run in order: `01_eda` → `02_risk_analysis` → `03_deep_case_investigation` → `04_visualizaciones`. Notebook 04 generates the final files in `docs/`.
