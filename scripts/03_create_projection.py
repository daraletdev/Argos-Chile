"""
Graph Projection Engine
=======================
Purpose: Projects the physical graph into Neo4j GDS memory for high-speed analysis.
Function: Creates a directed graph projection involving UnidadCompra, 
OrdenCompra_Item, and Proveedor to run PageRank and Community detection.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_ROOT_PASSWORD")

def create_projection():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # This Cypher command creates a 'Named Graph' in the GDS RAM
    projection_query = """
    CALL gds.graph.project(
      'argos_projection',
      ['UnidadCompra', 'Proveedor', 'OrdenCompra_Item'],
      {
        EMITIO: {orientation: 'NATURAL'},
        ADJUDICADA_A: {orientation: 'NATURAL'}
      }
    )
    """
    
    # We first drop it if it exists to avoid errors on re-runs
    drop_query = "CALL gds.graph.drop('argos_projection', false)"

    try:
        with driver.session() as session:
            print("[INFO] Cleaning existing projections...")
            session.run(drop_query)
            
            print("[INFO] Projecting Graph to GDS Memory...")
            result = session.run(projection_query).single()
            
            print(f"[SUCCESS] Projection created!")
            print(f"Nodes projected: {result['nodeCount']}")
            print(f"Relationships projected: {result['relationshipCount']}")
            
    except Exception as e:
        print(f"[ERROR] Projection failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    create_projection()