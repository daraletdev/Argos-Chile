"""
Risk Engine - Graph Intelligence
================================
Purpose: Executes graph algorithms (PageRank) and heuristic checks (Fragmentation) 
to assign risk scores to Suppliers and Agencies.
"""

from neo4j import GraphDatabase

class RiskEngine:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run_pagerank(self):
        """
        Calculates the influence of each Supplier in the network.
        High PageRank = Supplier has a dominant, potentially monopolistic position.
        """
        query = """
        CALL gds.pageRank.write('argos_projection', {
          writeProperty: 'pagerank_score'
        })
        """
        with self.driver.session() as session:
            print("[INFO] Calculating PageRank (Supplier Influence)...")
            session.run(query)
            print("[OK] PageRank scores written to nodes.")

    def detect_fragmentation(self, threshold_clp=6600000):
            """
            Flags Purchase Orders (AG - Compra Agil) that are suspiciously 
            close to the legal limit (approx 100 UTM).
            """
            lower_bound = threshold_clp * 0.95
            
            query = """
            MATCH (oc:OrdenCompra_Item {Modalidad: 'AG'})
            WHERE oc.Monto >= $lower AND oc.Monto <= $upper
            SET oc.risk_flag = 'Suspect_Fragmentation', oc.risk_score = 0.8
            RETURN count(oc) as flagged_count
            """
            with self.driver.session() as session:
                print(f"[INFO] Detecting potential fragmentation between {lower_bound} and {threshold_clp} CLP...")
                result = session.run(query, lower=lower_bound, upper=threshold_clp).single()
                print(f"[OK] Flagged {result['flagged_count']} suspicious AG orders.")

    def detect_fragmentation_clusters(self, threshold_clp=6600000):
        """
        Detects 'smurfing': Multiple small orders that combined in a single month 
        exceed the legal limit for the same Buyer-Seller pair.
        """
        query = """
        MATCH (u:UnidadCompra)-[:EMITIO]->(oc:OrdenCompra_Item {Modalidad: 'AG'})-[:ADJUDICADA_A]->(p:Proveedor)
        WITH u, p, oc.Fecha.month AS month, 
             count(oc) AS order_count, 
             sum(oc.Monto) AS total_clp,
             collect(oc.Monto) AS amounts,
             collect(oc.NombreEspecifico) AS descriptions,
             collect(oc.CodigoUnico) AS ids
        WHERE order_count > 1 AND total_clp > $threshold
        RETURN u.UnidadCompra AS agency, 
               p.Nombre AS vendor, 
               month, 
               order_count, 
               total_clp,
               amounts, 
               descriptions, 
               ids
        ORDER BY total_clp DESC
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query, threshold=threshold_clp)]

    def detect_agency_capture(self):
        """
        Detects extreme dependency: Institutions that concentrate their 
        Direct Deal budget on a single provider.
        """
        query = """
        MATCH (u:UnidadCompra)-[:EMITIO]->(oc:OrdenCompra_Item {Modalidad: 'TD'})-[:ADJUDICADA_A]->(p:Proveedor)
        WITH u, p, sum(oc.Monto) AS vendor_amount
        MATCH (u)-[:EMITIO]->(total_td:OrdenCompra_Item {Modalidad: 'TD'})
        WITH u, p, vendor_amount, sum(total_td.Monto) AS total_td_agency
        WHERE total_td_agency > 10000000 
        WITH u, p, vendor_amount, total_td_agency, (vendor_amount / total_td_agency) * 100 AS capture_percentage
        WHERE capture_percentage > 40
        RETURN u.UnidadCompra AS agency, p.Nombre AS vendor, capture_percentage, vendor_amount
        ORDER BY capture_percentage DESC
        """
        with self.driver.session() as session:
            return [dict(record) for record in session.run(query)]

    def close(self):
        self.driver.close()