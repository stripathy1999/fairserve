"""
Compute budget per incident baseline.

Inputs:
- data/processed/historical (parquet files)
- data/budget/service_type_to_department.json
- data/processed/department_budget_summary.json

Output:
- data/processed/budget_metrics.json

Computes:
- budget_per_incident = department_annual_budget / total_historical_incidents
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Configuration
HISTORICAL_DIR = "/home/dell/Desktop/fairserve-1/backend/data/processed/historical"
SERVICE_MAPPING_FILE = "/home/dell/Desktop/fairserve-1/backend/data/budget/service_type_to_department.json"
DEPT_SUMMARY_FILE = "/home/dell/Desktop/fairserve-1/backend/data/processed/department_budget_summary.json"
OUTPUT_FILE = "/home/dell/Desktop/fairserve-1/backend/data/processed/budget_metrics.json"

def main():
    print("Computing budget per incident metrics...")
    
    # Load service → department mapping
    with open(SERVICE_MAPPING_FILE, 'r') as f:
        service_to_dept = json.load(f)
    
    print(f"Loaded {len(service_to_dept)} service type mappings")
    
    # Load department budget summary
    with open(DEPT_SUMMARY_FILE, 'r') as f:
        dept_summary = json.load(f)
    
    # Create department → budget lookup
    dept_to_budget = {d['department']: d['total_spending'] for d in dept_summary}
    fiscal_year = dept_summary[0]['fiscal_year'] if dept_summary else 'Unknown'
    
    print(f"Loaded budget data for {len(dept_to_budget)} departments (FY {fiscal_year})")
    
    # Load historical incidents
    print("Loading historical incidents...")
    historical_path = Path(HISTORICAL_DIR)
    
    if not historical_path.exists():
        raise FileNotFoundError(f"Historical data directory not found: {HISTORICAL_DIR}")
    
    # Read all parquet files
    parquet_files = list(historical_path.rglob("*.parquet"))
    print(f"Found {len(parquet_files)} parquet files")
    
    if not parquet_files:
        raise FileNotFoundError("No parquet files found in historical directory")
    
    # Read and concatenate all files, extracting service_type from partition path
    dfs = []
    for pq_file in parquet_files:
        try:
            df = pd.read_parquet(pq_file)
            
            # Extract service_type from partition path if not in columns
            # Path format: .../service_type=<type>/...
            if 'service_type' not in df.columns:
                path_str = str(pq_file)
                if 'service_type=' in path_str:
                    # Extract service_type from path
                    service_type_part = [p for p in pq_file.parts if 'service_type=' in p]
                    if service_type_part:
                        service_type = service_type_part[0].replace('service_type=', '')
                        # URL decode if needed
                        import urllib.parse
                        service_type = urllib.parse.unquote(service_type)
                        df['service_type'] = service_type
            
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not read {pq_file}: {e}")
    
    if not dfs:
        raise ValueError("No valid parquet files could be read")
    
    hist_df = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(hist_df)} historical incidents")
    
    # Count incidents per service type
    service_counts = hist_df['service_type'].value_counts().to_dict()
    print(f"Found {len(service_counts)} unique service types")
    
    # Compute budget per incident for each service type
    budget_metrics = []
    
    for service_type, count in service_counts.items():
        # Get department for this service type
        department = service_to_dept.get(service_type)
        
        if not department:
            print(f"Warning: No department mapping for service type '{service_type}', skipping")
            continue
        
        # Get department budget
        dept_budget = dept_to_budget.get(department)
        
        if not dept_budget:
            print(f"Warning: No budget data for department '{department}', skipping")
            continue
        
        # Compute budget per incident
        budget_per_incident = dept_budget / count if count > 0 else 0.0
        
        budget_metrics.append({
            'service_type': service_type,
            'department': department,
            'total_historical_incidents': count,
            'department_annual_budget_usd': round(dept_budget, 2),
            'estimated_budget_per_incident_usd': round(budget_per_incident, 2),
            'fiscal_year': fiscal_year
        })
    
    # Sort by budget per incident (descending)
    budget_metrics.sort(key=lambda x: x['estimated_budget_per_incident_usd'], reverse=True)
    
    # Save output
    output_path = Path(OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(budget_metrics, f, indent=2)
    
    print(f"\nBudget metrics saved to {OUTPUT_FILE}")
    print(f"Service types processed: {len(budget_metrics)}")
    print(f"\nTop 5 service types by budget per incident:")
    for metric in budget_metrics[:5]:
        print(f"  {metric['service_type']}: ${metric['estimated_budget_per_incident_usd']:,.2f} per incident")
    
    print(f"\nBottom 5 service types by budget per incident:")
    for metric in budget_metrics[-5:]:
        print(f"  {metric['service_type']}: ${metric['estimated_budget_per_incident_usd']:,.2f} per incident")

if __name__ == "__main__":
    main()
