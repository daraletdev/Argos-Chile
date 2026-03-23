"""
Bronze Layer Data Crawler
=========================
Purpose: Handles robust HTTP connections and data extraction from remote blob storage.
Function: Implements retry logic, streaming downloads, zip extraction, and idempotency 
to ensure deterministic data retrieval for the Bronze layer.
"""

import os
import io
import zipfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

class ChileCompraCrawler:
    """Crawler specifically designed to handle the ChileCompra Azure Blob Storage."""
    
    def __init__(self, base_url: str):
        """
        Initializes the crawler with a base URL and a robust HTTP session.
        
        Args:
            base_url: The URL template containing a '{}' placeholder for the month.
        """
        self.base_url = base_url
        self.session = self._build_robust_session()

    def _build_robust_session(self) -> requests.Session:
        """Configures exponential backoff for network stability."""
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def download_month(self, year: int, month: int, target_dir: str) -> bool:
        """
        Downloads and extracts a specific month's ZIP file if it doesn't already exist.
        
        Args:
            year: The target year.
            month: The target month (1-12).
            target_dir: The destination directory (e.g., data/raw/2025).
            
        Returns:
            bool: True if successful or already exists, False if the file does not exist yet.
        """
        os.makedirs(target_dir, exist_ok=True)
        
        expected_file_1 = os.path.join(target_dir, f"{year}-{month}.csv")
        expected_file_2 = os.path.join(target_dir, f"{year}-{month:02d}.csv")
        
        if os.path.exists(expected_file_1) or os.path.exists(expected_file_2):
            print(f"[SKIP] Month {month:02d} already exists locally. Skipping download.")
            return True

        url = self.base_url.format(month)
        
        try:
            response = self.session.get(url, stream=True, timeout=(30, 300))
            if response.status_code == 404:
                return False
                
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            zip_buffer = io.BytesIO()
            
            with tqdm(total=total_size, unit='iB', unit_scale=True, desc=f"Downloading {year}-{month:02d}") as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        zip_buffer.write(chunk)
                        pbar.update(len(chunk))
            
            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer) as z:
                z.extractall(target_dir)
                
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Failed processing {year}-{month:02d}: {e}")
            raise