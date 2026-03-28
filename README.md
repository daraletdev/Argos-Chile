[🇨🇱 Versión en español](README_ES.md)

# Argos — Forensic Detection of Illegal Procurement Fragmentation in Chilean Public Spending

**Forensic analysis of 1.7 million Chilean state transactions · 2025**

> ChileCompra recognizes that "automated monitoring of fragmentation is an unresolved need of the system" (Navarrete, 2024). This project builds it.

---

## What is fragmentation and why does it matter?

When the State needs to purchase goods or services, the law establishes that **if the amount exceeds 1,000 UTM (~$66M CLP), it must go through a public tender** — where multiple suppliers compete and the State selects the best offer. This ensures transparency and the efficient use of public funds.

**Agile Purchase** (*Compra Ágil*) is an exception mechanism: it allows for quick purchases without a tender, but only if the individual order does not exceed 100 UTM (~$6.6M CLP).

**Fragmentation** occurs when an organization deliberately splits a large purchase into many small orders to stay below the threshold and bypass the public tender process. This is **illegal** according to DS 250 art. 13 and DS 661 art. 16, and can result in fines ranging from 10 to 100 UTM, in addition to administrative liability.

```
Public Tender (What should happen)           Fragmentation (What we detect)
─────────────────────────────────────────    ──────────────────────────────────────
  $702M Hardware purchase                     Order 001: $4.87M  ← below limit
         ↓                                    Order 002: $4.87M  ← below limit
  Public call for proposals                   Order 003: $4.87M  ← below limit
         ↓                                    ...
  Multiple suppliers compete                  Order 144: $4.87M  ← below limit
         ↓                                               ↓
  Best offer is selected                      Total: $702M → should have been tendered
```

---

## Main Finding

On April 10, 2025, the **6th Regiment "Chacabuco"** issued **144 identical purchase orders** in a single day to **CONSTRUCTORA Y COMERCIALIZADORA MOSIL LIMITADA**:

| | |
|---|---|
| Amount per order | $4,876,550 CLP — exactly the same for all 144 |
| Accumulated total | **$702,223,200 CLP** |
| Tender threshold excess | **10.6 times** |
| Source quote | `3365-52-COT25` — a single invitation split into 144 items |
| Description | Acquisition of hardware elements |
| % of selected limit | 73.9% — deliberately below the control threshold |

The 144 orders share the exact same amount, date, source quote, and description. This is not an administrative oversight.

### Scale of the Problem

| Metric | Value |
|---------|-------|
| Detected fragmentation cases | **2,214** |
| Total exposed amount | **$291.7 B CLP** |
| Affected sectors | Health, Education, Army, Police, Municipalities |
| Most chronic pair | U. de Chile Clinical Hospital → single supplier, **7 months of the year**, $1.01B CLP |

---

## Visualizations

**Top 15 cases by total exposed amount:**

![Top 15 fragmentation cases](docs/img/g2_fraccionamiento_top15.png)

**Distribution of accumulated amounts:**

![Amount distribution](docs/img/g3_distribucion.png)

**Chronic pairs — organizations fragmenting 6+ months of the year:**

![Chronic fragmentation](docs/img/g4_cronico.png)

**Chacabuco Regiment Case — MOSIL (144 identical orders):**

![Mosil Case](docs/img/g5_mosil.png)

**Order drilldown visualization:**

![Case drilldown](docs/img/g6_drilldown.png)

---

## Why Graphs and not SQL

Purchasing data is inherently relational. SQL can answer "how much did this organization spend?" but not "which suppliers systematically share the same hospitals?" or "which nodes have the highest structural power in the entire network?"

```
(PurchasingUnit) ──ISSUED──> (OrderLine_Item) ──AWARDED_TO──> (Supplier)
                                   └──CLASSIFIED_AS──> (Product)

1,976 organizations · 49,020 suppliers · 1,649,920 transactions
```

The graph also allows running **PageRank** over the network — measuring not just who sells more, but who holds structural power, independent of sales volume.

---

## Stack

| Component | Technology |
|-----------|-----------|
| Data Source | Mercado Público Chile (Azure Blob Storage) |
| ETL | Python · pandas |
| Storage | Neo4j 5 (Property Graph) |
| Graph Algorithms | Neo4j GDS (PageRank, projections) |
| Analysis & Visualization | Python · pandas · matplotlib |

### Pipeline

```
00_download_bronze.py    download CSVs from Mercado Público
01_process_silver.py     cleaning and normalization
02_bulk_ingestion.py     load into Neo4j via APOC batch
03_create_projection.py  GDS projection
04_run_analytics.py      PageRank + pattern detection
```

---

## Case Classification

Each case is evaluated across three independent dimensions (1–3 points each):

| Dimension | 1 point | 2 points | 3 points |
|-----------|---------|---------|---------|
| **Forensic Evidence** | Varied amounts/descriptions | >80% in one of the two criteria | >80% in both or single source quote |
| **Chronicity** | 1–2 months | 3–5 months | 6+ months of the year |
| **Scale** | <10x the threshold | 10–50x | >50x |

`CRITICAL` ≥7 pts · `HIGH` ≥6 · `MEDIUM` ≥4 · `LOW` <4

Chronicity is heavily weighted: an organization fragmenting the same contract over 7 different months cannot argue that the total amount was unpredictable. This follows the Comptroller General's (CGR) ruling for the Municipality of La Cisterna.

---

## Installation

**Requirements:** Python 3.11+, Neo4j 5 with APOC and GDS, Docker

```bash
git clone https://github.com/daraletdev/Argos-Chile
cd Argos-Chile
uv sync
cp .env.example .env          # configure NEO4J_ROOT_PASSWORD
docker compose up -d
uv run python scripts/00_download_bronze.py
uv run python scripts/01_process_silver.py
uv run python scripts/02_bulk_ingestion.py
uv run python scripts/03_create_projection.py
uv run python scripts/04_run_analytics.py
cd notebooks && jupyter lab
```

---

## Legal Framework

- DS 250 art. 13 — defines and prohibits fragmentation.
- DS 661 art. 16 (December 2024) — new regulation, reinforcing the prohibition.
- CGR Ruling, Municipality of La Cisterna — precedent on amount unpredictability.
- Navarrete Millón, M. (2024). *Fragmentación en compras públicas*. ISBN 978-956-405-179-6.
- Sanctions: 10 to 100 UTM + administrative liability.

---

## Methodological Warning

The findings are statistical indications based on objective patterns in public data. They do not constitute proof of fraud or a legal determination. Each case requires independent documentary verification.

---

*Data: Mercado Público Chile 2025 · License: MIT*
