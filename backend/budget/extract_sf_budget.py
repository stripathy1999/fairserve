"""
Extract SF Budget Data from local parquet files.

Source: data/budget/fy2026_batch_*.parquet
Extracts minimal slice: spending data for latest fiscal year only.

Output: data/budget/sf_budget_raw.json
"""

import duckdb
import json
from pathlib import Path

# Configuration
PARQUET_PATTERN = "/home/dell/Desktop/fairserve-1/backend/data/budget/fy2026_batch_*.parquet"
OUTPUT_FILE = "/home/dell/Desktop/fairserve-1/backend/data/budget/sf_budget_raw.json"

# Required fields
FIELDS = [
    "fiscal_year",
    "revenue_or_spending",
    "department",
    "organization_group",
    "program",
    "character",
    "budget"
]

def main():
    print("Extracting SF Budget data from local parquet files...")
    
    # Step 1: Connect to DuckDB and read parquet files
    print(f"Step 1: Reading parquet files matching pattern: {PARQUET_PATTERN}")
    
    con = duckdb.connect(':memory:')
    
    # Read all matching parquet files
    # Note: parquet files have: budget, revenue_or_spending, department_code, department, program_code, program, fiscal_year
    # We'll select what's available and add placeholders for missing fields
    query = f"""
    SELECT 
        fiscal_year,
        revenue_or_spending,
        department,
        department_code as organization_group,
        program,
        program_code,
        '' as character,
        budget
    FROM read_parquet('{PARQUET_PATTERN}')
    WHERE revenue_or_spending = 'Spending'
    """
    
    result = con.execute(query).fetchdf()
    
    if result.empty:
        raise ValueError("No spending data found in parquet files")
    
    print(f"Loaded {len(result)} spending records")
    
    # Step 2: Get latest fiscal year
    print("Step 2: Determining latest fiscal year...")
    latest_year = result['fiscal_year'].max()
    print(f"Latest fiscal year: {latest_year}")
    
    # Step 3: Filter for latest year
    print(f"Step 3: Filtering for FY {latest_year}...")
    latest_data = result[result['fiscal_year'] == latest_year]
    
    print(f"Total records for FY {latest_year}: {len(latest_data)}")
    
    # Step 4: Convert to list of dicts
    all_records = latest_data.to_dict('records')
    
    # Step 5: Save to file
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "fiscal_year": str(latest_year),
            "record_count": len(all_records),
            "records": all_records
        }, f, indent=2)
    
    print(f"Budget data saved to {OUTPUT_FILE}")
    print(f"Fiscal Year: {latest_year}")
    print(f"Records: {len(all_records)}")
    
    con.close()

if __name__ == "__main__":
    main()
