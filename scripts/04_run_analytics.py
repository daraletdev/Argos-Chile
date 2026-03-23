"""
Analytics Execution Pipeline - Forensic Edition
==============================================
Purpose: Orchestrates the execution of Graph Data Science and Deep Forensic queries.
Function: Runs PageRank, Simple Fragmentation, Cluster Detection, and Agency Capture.
"""

import sys
import os
from pathlib import Path

# Add project root to PYTHONPATH to ensure src is discoverable
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from dotenv import load_dotenv
from src.argos.analytics.risk_engine import RiskEngine

load_dotenv()

def main():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = os.getenv("NEO4J_ROOT_PASSWORD")

    if not password:
        print("[ERROR] Password not found in .env")
        return

    # Initialize the forensic engine
    engine = RiskEngine(uri, user, password)

    try:
        print("=== Argos: Starting Deep Risk Analysis ===")
        
        # 1. SURFACE ANALYSIS: Monopoly Power
        # Writes 'pagerank_score' to nodes to measure structural influence
        engine.run_pagerank()
        
        # 2. SURFACE ANALYSIS: Boundary Orders
        # Flags AG orders suspiciously close to the limit
        engine.detect_fragmentation(threshold_clp=6600000)
        
        # 3. DEEP ANALYSIS: Smurfing (Fragmentation Clusters)
        # Finds patterns of split contracts between same Agency-Vendor pairs
        print("[INFO] Analyzing Fragmentation Clusters (Smurfing)...")
        frag_clusters = engine.detect_fragmentation_clusters()
        print(f"[OK] Found {len(frag_clusters)} potential smurfing cases.")
        
        # 4. DEEP ANALYSIS: State Capture (Agency Marriage)
        # Finds Agencies that give most of their Direct Deal budget to one vendor
        print("[INFO] Analyzing Agency Capture (Direct Deal Concentration)...")
        captures = engine.detect_agency_capture()
        print(f"[OK] Found {len(captures)} high-risk capture patterns.")
        
        print("\n[SUCCESS] All forensic engines completed.")
        print("[INFO] You can now visualize detailed tables in the Jupyter Notebook.")
        
    except Exception as e:
        print(f"\n[ERROR] Analytics pipeline failed: {e}")
    finally:
        engine.close()

if __name__ == "__main__":
    main()