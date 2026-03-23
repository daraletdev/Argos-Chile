"""
Execute Bronze Layer Download
=============================
Purpose: Entry point to stage raw procurement data locally.
Usage: uv run python scripts/00_download_bronze.py
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.argos.etl.crawler import ChileCompraCrawler

def main():
    print("=== Argos: Initiating Bronze Layer Staging ===")
    target_year = 2025
    url_template = f"https://transparenciachc.blob.core.windows.net/oc-da/{target_year}-{{}}.zip"
    target_directory = f"data/raw/{target_year}"
    
    crawler = ChileCompraCrawler(base_url=url_template)
    
    for month in range(1, 13):
        success = crawler.download_month(year=target_year, month=month, target_dir=target_directory)
        if success:
            print(f"[OK] Month {month:02d} safely stored in {target_directory}")
        else:
            print(f"[SKIP] Month {month:02d} not published by the government yet.")
            
    print("\n[SUCCESS] Bronze Layer fully staged and ready for EDA.")

if __name__ == "__main__":
    main()