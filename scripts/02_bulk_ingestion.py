"""
Gold Layer Ingestion Engine
===========================
Purpose: Translates Silver Layer CSVs into a Property Graph in Neo4j.
Function: Creates unique constraints, nodes, and relationships using optimized
batch ingestion (apoc.periodic.iterate) for millions of records.
"""

import os
import glob
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_ROOT_PASSWORD")

class GraphIngestor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def setup_constraints(self):
        """Creates indexes and constraints to ensure uniqueness and fast lookups."""
        queries = [
            "CREATE CONSTRAINT unique_agency IF NOT EXISTS FOR (u:UnidadCompra) REQUIRE u.RutUnidadCompra IS UNIQUE",
            "CREATE CONSTRAINT unique_vendor IF NOT EXISTS FOR (p:Proveedor) REQUIRE p.CodigoProveedor IS UNIQUE",
            "CREATE CONSTRAINT unique_product IF NOT EXISTS FOR (pr:Producto) REQUIRE pr.CategoriaGenerica IS UNIQUE",
            "CREATE CONSTRAINT unique_oc IF NOT EXISTS FOR (oc:OrdenCompra_Item) REQUIRE oc.CodigoUnico IS UNIQUE"
        ]

        with self.driver.session() as session:
            for query in queries:
                session.run(query)
        print("[OK] Graph constraints and indexes established.")

    def ingest_month(self, csv_filename: str):
        """
        Uses APOC to read the CSV in batches and build the graph.
        We use the 'file:///processed/...' path because that's how we mounted it in Docker.
        """
        cypher_query = f"""
        CALL apoc.periodic.iterate(
            "LOAD CSV WITH HEADERS FROM 'file:///processed/2025/{csv_filename}' AS row RETURN row",
            "
            MERGE (u:UnidadCompra {{RutUnidadCompra: row.tax_id}})
            ON CREATE SET
                u.UnidadCompra = row.agency_name,
                u.Sector = row.sector,
                u.Region = row.region

            MERGE (p:Proveedor {{CodigoProveedor: toString(toInteger(toFloat(row.vendor_id)))}})
            ON CREATE SET
                p.Nombre = row.vendor_name

            MERGE (pr:Producto {{CategoriaGenerica: coalesce(row.generic_product, 'Unspecified')}})

            MERGE (oc:OrdenCompra_Item {{CodigoUnico: row.order_id + '-' + row.item_id}})
            ON CREATE SET
                oc.CodigoPadre = row.order_id,
                oc.Monto = toFloat(row.total_amount),
                oc.Cantidad = toFloat(row.quantity),
                oc.PrecioUnitario = toFloat(row.unit_price),
                oc.Fecha = date(substring(row.acceptance_date, 0, 10)),
                oc.Estado = row.status,
                oc.Modalidad = row.procurement_type,
                oc.NombreEspecifico = row.product_name,
                oc.Detalle = row.description

            MERGE (u)-[:EMITIO]->(oc)
            MERGE (oc)-[:ADJUDICADA_A]->(p)
            MERGE (oc)-[:CLASIFICA_COMO]->(pr)
            ",
            {{batchSize: 10000, parallel: true, retries: 3}}
        )
        """
        with self.driver.session() as session:
            result = session.run(cypher_query)
            stats = result.single()
            print(f"[SUCCESS] {csv_filename} ingested: {stats['batches']} batches completed.")

def main():
    print("=== Argos: Initiating Gold Layer Graph Ingestion ===")

    if not NEO4J_PASSWORD:
        print("[ERROR] NEO4J_ROOT_PASSWORD not found in .env file.")
        return

    # Find the processed CSVs
    target_year = 2025
    silver_dir = f"data/processed/{target_year}"
    csv_files = [os.path.basename(f) for f in glob.glob(os.path.join(silver_dir, "*.csv"))]

    if not csv_files:
        print(f"[ERROR] No processed files found in {silver_dir}.")
        return

    ingestor = GraphIngestor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        print("1. Setting up Graph Topology...")
        ingestor.setup_constraints()

        print(f"2. Ingesting {len(csv_files)} months into Neo4j...")
        for filename in csv_files:
            ingestor.ingest_month(filename)

        print("\n[SUCCESS] Gold Layer Graph fully constructed and ready for Graph Data Science!")
    except Exception as e:
        print(f"\n[ERROR] Neo4j Ingestion failed: {e}")
    finally:
        ingestor.close()

if __name__ == "__main__":
    main()