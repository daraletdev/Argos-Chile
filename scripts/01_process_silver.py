"""
Execute Silver Layer Processing
===============================
Purpose: Orchestrates the ETL pipeline from the Bronze to the Silver layer.
Usage: uv run python scripts/01_process_silver.py
"""

import sys
import os
import glob
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.argos.etl.cleaner import DataSanitizer

def main():
    print("=== Argos: Initiating Silver Layer Processing ===")
    target_year = 2025
    
    bronze_dir = f"data/raw/{target_year}"
    silver_dir = f"data/processed/{target_year}"
    
    csv_files = glob.glob(os.path.join(bronze_dir, "*.csv"))
    
    if not csv_files:
        print(f"[ERROR] No raw datasets found in {bronze_dir}.")
        return

    sanitizer = DataSanitizer()
    successful_files = 0
    
    print(f"[INFO] Found {len(csv_files)} files. Starting forensic sanitization...")
    
    for file_path in tqdm(csv_files, desc="Processing Months"):
        filename = os.path.basename(file_path)
        output_path = os.path.join(silver_dir, filename)
        
        if os.path.exists(output_path):
            print(f"\n[SKIP] {filename} is already in the Silver Layer.")
            successful_files += 1
            continue
            
        if sanitizer.process_file(input_path=file_path, output_path=output_path):
            successful_files += 1
            
    print(f"\n[SUCCESS] {successful_files}/{len(csv_files)} files staged in Silver Layer.")
    print(f"[INFO] Data is now forensic-grade and ready for Neo4j ingestion.")

if __name__ == "__main__":
    main()