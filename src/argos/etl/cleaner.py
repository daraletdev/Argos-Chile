"""
Silver Layer Data Sanitizer
===========================
Purpose: Transforms raw Bronze datasets into clean, forensic-grade Silver datasets.
Function: Extracts strictly necessary columns, standardizes datatypes (handling Chilean 
number formats), and drops invalid or canceled transactions to prepare for Neo4j.
"""

import os
import pandas as pd

class DataSanitizer:
    """Handles the forensic cleaning and transformation of procurement data."""
    
    # Map raw Spanish headers to clean English headers for the Graph Model
    COLUMN_MAP = {
        "Codigo": "order_id",
        "IDItem": "item_id",
        "RutUnidadCompra": "tax_id",
        "UnidadCompra": "agency_name",
        "sector": "sector",
        "RegionUnidadCompra": "region",
        "CodigoProveedor": "vendor_id",
        "NombreProveedor": "vendor_name",
        "FechaAceptacion": "acceptance_date",
        "Estado": "status",
        "CodigoAbreviadoTipoOC": "procurement_type",
        "NombreroductoGenerico": "generic_product",
        "Nombre": "product_name",
        "Descripcion/Obervaciones": "description",
        "cantidad": "quantity",
        "precioNeto": "unit_price",
        "TotalNetoOC": "total_amount"
    }

    def __init__(self):
        # Valid states extracted from EDA dictionary. 
        # We only care about money that is moving or committed.
        self.valid_states = [
            "Aceptada", 
            "Recepcion Conforme", 
            "En proceso", 
            "Enviada a proveedor",
            "4", "5", "6", "12" # Stringified numbers for compatibility
        ]

    def _clean_numeric(self, series: pd.Series) -> pd.Series:
        """
        Converts Chilean number formats (e.g., '1.234.567,89') to standard floats.
        Removes thousand separator dots first, then replaces decimal commas with dots.
        """
        cleaned = series.astype(str)\
            .str.replace('.', '', regex=False)\
            .str.replace(',', '.', regex=False)
        return pd.to_numeric(cleaned, errors='coerce')

    def process_file(self, input_path: str, output_path: str) -> bool:
        """
        Reads a raw Bronze CSV, applies forensic transformations, and saves the Silver version.
        
        Args:
            input_path: Path to the raw CSV (Bronze Layer).
            output_path: Path to save the processed CSV (Silver Layer).
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # 1. Evaluate existing columns without loading the full dataset to RAM
            first_row = pd.read_csv(input_path, sep=';', encoding='latin-1', nrows=0)
            
            # Map the target columns to the actual ones found in the CSV
            actual_cols = [col for col in self.COLUMN_MAP.keys() if col in first_row.columns]
            
            # Load only the required columns
            df = pd.read_csv(
                input_path, 
                sep=';', 
                encoding='latin-1', 
                usecols=actual_cols,
                low_memory=False
            )
            
            # Rename to English headers immediately for internal processing
            df = df.rename(columns={k: v for k, v in self.COLUMN_MAP.items() if k in df.columns})
            
            # 2. Filter Valid Transactions (Keep only successful/ongoing purchases)
            if "status" in df.columns:
                df["status"] = df["status"].astype(str).str.strip()
                df = df[df["status"].isin(self.valid_states)]
                
            # 3. Standardize Financial Variables using the robust numeric cleaner
            numeric_cols = ["total_amount", "unit_price", "quantity"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = self._clean_numeric(df[col])
            
            # 4. Filter out transactions with zero or negative amounts
            if "total_amount" in df.columns:
                df = df[df["total_amount"] > 0]
                
            # 5. Standardize Dates
            if "acceptance_date" in df.columns:
                df["acceptance_date"] = pd.to_datetime(df["acceptance_date"], errors='coerce')
                df = df.dropna(subset=["acceptance_date"])
            
            # 6. Text Sanitization (Hardened for Neo4j CSV Import)
            # We replace quotes, newlines, tabs, and semicolons to prevent parser crashes.
            text_cols = [
                "product_name", "description", "generic_product", 
                "agency_name", "vendor_name"
            ]
            for col in text_cols:
                if col in df.columns:
                    # Convert to string and strip
                    df[col] = df[col].astype(str).str.strip()
                    
                    # STEP 1: Replace double quotes with single quotes to avoid CSV breaking
                    df[col] = df[col].str.replace('"', "'", regex=False)
                    
                    # STEP 2: Replace separators/newlines with a single space
                    df[col] = df[col].str.replace(r'[\n\r\t,;]+', ' ', regex=True)
           
            # 6.5. Normalize vendor_id — must always be a clean integer string
            if "vendor_id" in df.columns:
                def _normalize_id(val):
                    try:
                        return str(int(float(val)))
                    except (ValueError, TypeError):
                        return None
                df["vendor_id"] = df["vendor_id"].map(_normalize_id)

            # 7. Drop rows missing critical Primary Keys (Cannot build graph without them)
            critical_pks = ["order_id", "item_id", "tax_id", "vendor_id"]
            existing_pks = [col for col in critical_pks if col in df.columns]
            df = df.dropna(subset=existing_pks)
            
            # 8. Save to Silver Layer (UTF-8, comma separated, clean formats)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df.to_csv(output_path, sep=',', encoding='utf-8', index=False)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to sanitize {input_path}: {e}")
            return False