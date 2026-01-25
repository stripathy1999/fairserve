"""
Compute department-level budget summary.

Input: data/budget/sf_budget_raw.json
Output: data/processed/department_budget_summary.json

For each department:
- total_spending
- labor_share (Salaries + Benefits / total)
- ops_share (remaining)
- programs_count
"""

import json
from pathlib import Path
from collections import defaultdict

# Configuration
INPUT_FILE = "/home/dell/Desktop/fairserve-1/backend/data/budget/sf_budget_raw.json"
OUTPUT_FILE = "/home/dell/Desktop/fairserve-1/backend/data/processed/department_budget_summary.json"

# Labor-related budget characters
LABOR_CHARACTERS = {"Salaries", "Benefits", "Mandatory Fringe Benefits", "Fringe Benefits"}

def main():
    print("Computing department budget summary...")
    
    # Load raw budget data
    with open(INPUT_FILE, 'r') as f:
        budget_data = json.load(f)
    
    fiscal_year = budget_data['fiscal_year']
    records = budget_data['records']
    
    print(f"Processing {len(records)} records for FY {fiscal_year}")
    
    # Aggregate by department
    dept_data = defaultdict(lambda: {
        'total_spending': 0.0,
        'labor_spending': 0.0,
        'programs': set()
    })
    
    for record in records:
        dept = record.get('department', 'Unknown')
        character = record.get('character', '')
        budget_str = record.get('budget', '0')
        program = record.get('program', '')
        
        # Parse budget amount
        try:
            budget_amount = float(budget_str)
        except (ValueError, TypeError):
            continue
        
        dept_data[dept]['total_spending'] += budget_amount
        
        if character in LABOR_CHARACTERS:
            dept_data[dept]['labor_spending'] += budget_amount
        
        if program:
            dept_data[dept]['programs'].add(program)
    
    # Compute summary metrics
    summary = []
    for dept, data in dept_data.items():
        total = data['total_spending']
        labor = data['labor_spending']
        
        labor_share = labor / total if total > 0 else 0.0
        ops_share = 1.0 - labor_share
        
        summary.append({
            'department': dept,
            'fiscal_year': fiscal_year,
            'total_spending': round(total, 2),
            'labor_share': round(labor_share, 4),
            'ops_share': round(ops_share, 4),
            'programs_count': len(data['programs'])
        })
    
    # Sort by total spending (descending)
    summary.sort(key=lambda x: x['total_spending'], reverse=True)
    
    # Save output
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Department summary saved to {OUTPUT_FILE}")
    print(f"Departments processed: {len(summary)}")
    print(f"\nTop 5 departments by spending:")
    for dept in summary[:5]:
        print(f"  {dept['department']}: ${dept['total_spending']:,.0f}")

if __name__ == "__main__":
    main()
