import requests
import pandas as pd
import time
import os
import sys

# API Endpoint for San Francisco Budget Data
BASE_URL = "https://data.sfgov.org/resource/xdgd-c79v.json"

# Columns to fetch
COLUMNS = [
    "budget",
    "revenue_or_spending",
    "department_code",
    "department",
    "program_code",
    "program",
    "fiscal_year"
]

BATCH_SIZE = 2000
OUTPUT_DIR = "data/budget"
FISCAL_YEAR = "2026"

def fetch_and_save_data():
    """Fetches data for FY 2026 in batches and saves each as a Parquet file."""
    
    # Ensure output directory exists (redundant safety)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    offset = 0
    total_rows = 0
    batch_num = 0
    
    # SoQL Query construction
    select_fields = ",".join(COLUMNS)
    where_clause = f"fiscal_year='{FISCAL_YEAR}'"
    
    print(f"Fetching data for Fiscal Year: {FISCAL_YEAR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    while True:
        params = {
            "$select": select_fields,
            "$where": where_clause,
            "$limit": BATCH_SIZE,
            "$offset": offset,
            "$order": ":id" # Stable sort
        }
        
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Helper: ensure all expected columns exist, even if missing in a batch
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = None 
            
            # Enforce column order and selection
            df = df[COLUMNS]

            # Save batch to Parquet
            output_path = os.path.join(OUTPUT_DIR, f"fy{FISCAL_YEAR}_batch_{batch_num}.parquet")
            df.to_parquet(output_path, index=False)
            
            count = len(df)
            total_rows += count
            offset += count
            batch_num += 1
            
            print(f"Saved batch {batch_num} ({count} rows) to {output_path}. Total: {total_rows}")
            
            if count < BATCH_SIZE:
                break
                
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error fetching batch at offset {offset}: {e}")
            sys.exit(1)

    print(f"Done! Total rows fetched: {total_rows}")

if __name__ == "__main__":
    fetch_and_save_data()
