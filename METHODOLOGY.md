# Argos — Documentación Técnica y Metodología

---

## Estructura del proyecto

```
argos/
├── scripts/
│   ├── 00_download_bronze.py      descarga de datos crudos
│   ├── 01_process_silver.py       limpieza y normalización
│   ├── 02_bulk_ingestion.py       carga en Neo4j
│   ├── 03_create_projection.py    proyección GDS
│   └── 04_run_analytics.py        ejecución de algoritmos
├── src/argos/
│   ├── etl/
│   │   ├── crawler.py             cliente HTTP para Mercado Público
│   │   └── cleaner.py             DataSanitizer — limpieza forense
│   └── analytics/
│       └── risk_engine.py         motores de detección de riesgo
├── notebooks/
│   ├── 01_eda.ipynb               exploración de datos
│   ├── 02_risk_analysis.ipynb     análisis de fraccionamiento
│   ├── 03_deep_case_investigation.ipynb   investigación automática de casos
│   └── 04_visualizaciones.ipynb   gráficos y exportación de reportes
├── docs/
│   ├── reporte_fraccionamiento_final.md   reporte completo (generado)
│   └── fraccionamiento_blindado.csv       datos completos (generado)
├── docker-compose.yml
└── pyproject.toml
```

---

## Pipeline de datos

### Bronze layer — datos crudos

`scripts/00_download_bronze.py` descarga los archivos ZIP mensuales desde el blob storage de Mercado Público:

```
https://transparenciachc.blob.core.windows.net/oc-da/2025-{mes}.zip
```

Cada archivo contiene las órdenes de compra aceptadas del mes en formato CSV con separador `;` y encoding `latin-1`.

### Silver layer — datos limpios

`src/argos/etl/cleaner.py` aplica las siguientes transformaciones:

- Selección de 17 columnas estratégicas del modelo de grafos
- Filtrado a estados válidos: Aceptada, Recepción Conforme, En proceso, Enviada a proveedor
- Normalización de montos en formato chileno (`1.234.567,89` → `1234567.89`)
- Eliminación de transacciones con monto cero o negativo
- Sanitización de texto para Neo4j (comillas, saltos de línea, punto y coma)
- Normalización de `CodigoProveedor` — conversión de floats como `25638.0` a enteros `25638` para evitar nodos duplicados en el grafo

### Gold layer — grafo Neo4j

`scripts/02_bulk_ingestion.py` construye el grafo mediante APOC batch:

```cypher
MERGE (u:UnidadCompra {RutUnidadCompra: row.RutUnidadCompra})
MERGE (p:Proveedor {CodigoProveedor: toString(toInteger(toFloat(row.CodigoProveedor)))})
MERGE (pr:Producto {CategoriaGenerica: row.NombreroductoGenerico})
MERGE (oc:OrdenCompra_Item {CodigoUnico: row.Codigo + '-' + row.IDItem})
MERGE (u)-[:EMITIO]->(oc)
MERGE (oc)-[:ADJUDICADA_A]->(p)
MERGE (oc)-[:CLASIFICA_COMO]->(pr)
```

**Constraints de unicidad:**
- `UnidadCompra.RutUnidadCompra`
- `Proveedor.CodigoProveedor`
- `Producto.CategoriaGenerica`
- `OrdenCompra_Item.CodigoUnico`

**Escala del grafo (2025):**

| Nodo | Total |
|------|-------|
| OrdenCompra_Item | 1,649,920 |
| Producto | 66,737 |
| Proveedor | 49,020 |
| UnidadCompra | 1,976 |

---

## Metodología de detección

### Definición operacional de fraccionamiento

Un par organismo–proveedor en un mes dado se considera caso de fraccionamiento cuando:

1. La modalidad de todas las órdenes es `AG` (Compra Ágil)
2. El número de órdenes en el mes es mayor a 1
3. El monto acumulado del mes supera **1.000 UTM ($66M CLP)** — umbral a partir del cual la ley exige licitación pública

El umbral de 1.000 UTM (no 100 UTM) es deliberado: el análisis busca casos donde el Estado tenía **obligación legal de licitar** y no lo hizo, no simplemente casos donde se usó la Compra Ágil.

### Indicadores por caso

Para cada par detectado se calculan los siguientes indicadores a partir de las órdenes individuales:

| Indicador | Descripción | Relevancia |
|-----------|-------------|------------|
| `Pct_Monto_Identico` | % de órdenes con el mismo monto exacto | Montos idénticos al peso son evidencia de emisión en lote |
| `Pct_Desc_Identica` | % de órdenes con la misma descripción | Mismo bien o servicio dividido artificialmente |
| `Cotizacion_Base` | Código de la cotización de origen | Una sola cotización dividida en N ítems es la evidencia más directa |
| `Cotizaciones_Unicas` | Número de cotizaciones distintas | 1 = una sola compra fragmentada |
| `Monto_Medio / LIMITE_ORDEN` | Monto unitario como % del límite AG | Valores cercanos al 100% indican ajuste deliberado |

### Sistema de puntuación

Cada caso recibe entre 1 y 3 puntos en tres dimensiones independientes:

**Dimensión A — Evidencia forense:**
- 3 pts: `Pct_Monto_Identico > 80%` AND `Pct_Desc_Identica > 80%`, o `Cotizaciones_Unicas == 1`
- 2 pts: uno de los dos criterios supera 80%
- 1 pt: variedad en montos y descripciones

**Dimensión B — Cronicidad:**
- 3 pts: el mismo par aparece en 6 o más meses del año
- 2 pts: 3 a 5 meses
- 1 pt: 1 a 2 meses

La cronicidad tiene peso propio porque elimina el argumento de imprevisibilidad del monto total. Un organismo que fracciona el mismo contrato durante 7 meses consecutivos no puede argumentar que no anticipaba que el total superaría el umbral de licitación. Esto sigue el criterio del dictamen de la Contraloría General de la República en el caso Municipalidad de La Cisterna.

**Dimensión C — Escala:**
- 3 pts: multiplicador ≥ 50x el umbral
- 2 pts: 10x–50x
- 1 pt: <10x

**Clasificación final:**

| Nivel | Puntuación | Criterio |
|-------|-----------|---------|
| CRÍTICO | ≥ 7 | Todas las dimensiones altas simultáneamente |
| ALTO | ≥ 6 | Dos dimensiones con puntuación alta |
| MEDIO | ≥ 4 | Una dimensión fuerte |
| BAJO | < 4 | Volumen supera el umbral legal — incluidos por completitud |

---

## Limitaciones conocidas

**Sobre los datos:**
- El campo `NombreEspecifico` de las órdenes puede estar truncado en la fuente original, afectando el cálculo de `Pct_Desc_Identica`
- `CodigoProveedor` puede venir como entero o float en distintos meses — corregido en el cleaner, pero versiones anteriores del grafo pueden tener nodos duplicados

**Sobre la metodología:**
- El análisis no evalúa si el bien o servicio era técnicamente indivisible por su naturaleza
- No considera contexto operacional ni urgencias formalmente declaradas
- Los casos clasificados como BAJO pueden incluir compras diversas legítimas a un proveedor habitual donde el volumen acumulado supera el umbral sin que los ítems sean equivalentes
- La intención del funcionario no es determinable con datos de transacciones

**Sobre el alcance legal:**
- Los hallazgos son indicios estadísticos, no prueba de fraude
- La determinación de ilegalidad corresponde a la Contraloría General de la República o a las fiscalías competentes
- El análisis no cubre fraude en licitaciones públicas, trato directo irregular, ni otros tipos de irregularidades en compras públicas

---

## Marco legal y referencias

**Normativa:**
- Ley 19.886 de Bases sobre Contratos Administrativos de Suministro y Prestación de Servicios
- DS 250 art. 13 — definición de fragmentación y prohibición expresa
- DS 661 art. 16 (diciembre 2024) — nuevo reglamento, refuerza la prohibición

**Jurisprudencia:**
- Dictamen CGR, caso Municipalidad de La Cisterna — rechazó el argumento de centros de costo independientes cuando el total supera 1.000 UTM en compras al mismo proveedor

**Bibliografía:**
- Navarrete Millón, M. (2024). *Fragmentación en compras públicas*. ISBN 978-956-405-179-6. ChileCompra / Pontificia Universidad Católica de Chile. El autor, encargado de Transparencia de ChileCompra, define fragmentación como "la mala práctica de subdividir la compra de un conjunto de bienes o servicios requeridos por un organismo público en procesos repetitivos de menor cuantía con el objeto de eludir el uso de procedimientos de contratación que están sujetos a mayores controles y exigencias administrativas". Reconoce además que el monitoreo automatizado es una necesidad no resuelta del sistema.

**Fuente de datos:**
- Mercado Público Chile — datos abiertos de órdenes de compra 2025
- URL: `https://transparenciachc.blob.core.windows.net/oc-da/`

---

## Reproducibilidad

Para reproducir exactamente los resultados de este análisis:

```bash
# Verificar que el grafo no tiene nodos duplicados de CodigoProveedor
# (debería retornar 0 tras una ingesta limpia)
MATCH (p1:Proveedor), (p2:Proveedor)
WHERE toInteger(toFloat(toString(p1.CodigoProveedor))) =
      toInteger(toFloat(toString(p2.CodigoProveedor)))
  AND elementId(p1) < elementId(p2)
RETURN count(*) AS duplicados
```

```bash
# Verificar escala del grafo
MATCH (n) RETURN labels(n)[0] AS Tipo, count(n) AS Total ORDER BY Total DESC
```

Los notebooks están diseñados para ejecutarse en orden: `01_eda` → `02_risk_analysis` → `03_deep_case_investigation` → `04_visualizaciones`. El notebook 04 genera los archivos finales en `docs/`.
