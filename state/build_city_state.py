
import pandas as pd
import json
import numpy as np

# --- Configuration ---
FAIRNESS_FILE = "data/processed/fairness_metrics.json"
SIGNALS_FILE = "data/processed/neighborhood_signals.json"
OUTPUT_FILE = "data/processed/city_state.json"

# --- Governance Constitution (Hardcoded) ---
GOVERNANCE = {
    "worst_k": 3,
    "constraints": {
        "min_worst_k_improvement": 0.15,
        "max_neighborhood_harm": 0.05,
        "max_backlog_growth": 0.10,
        "citywide_p90_must_not_worsen": True
    }
}

# --- Policy Search Space (Hardcoded) ---
POLICY_SPACE = {
    "capacity_shift_pct": [0.0, 0.3],
    "efficiency_bonus_pct": [0.0, 0.1],
    "max_reassignments": [0, 3]
}

def main():
    # 1. Load Input Data
    try:
        with open(FAIRNESS_FILE, 'r') as f:
            fairness_data = json.load(f)
        with open(SIGNALS_FILE, 'r') as f:
            signals_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading inputs: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # Convert to DataFrames for easier manipulation
    fairness_df = pd.DataFrame(fairness_data)
    signals_df = pd.DataFrame(signals_data)

    if fairness_df.empty:
        print("Fairness metrics empty.")
        return

    # 1. Select Service Type
    # Hardcode "Encampment" for now as requested
    target_service = "Encampment"
    
    # Check if target exists, if not pick first
    unique_services = fairness_df['service_type'].unique()
    if target_service not in unique_services:
        if len(unique_services) > 0:
            target_service = unique_services[0]
            print(f"Service '{target_service}' not found, defaulting to '{target_service}'")
        else:
            print("No services found.")
            return

    # Filter Data
    f_df = fairness_df[fairness_df['service_type'] == target_service].copy()
    s_df = signals_df[signals_df['service_type'] == target_service].copy()

    # 2. City-level Context
    # p50_hr median of neighborhoods
    city_p50 = f_df['p50_hr'].median()
    
    # city_p90_hr should be unique for the service in fairness_df
    city_p90 = f_df['city_p90_hr'].iloc[0] if not f_df.empty else 0
    
    # service volume (sum N)
    total_incidents = f_df['N'].sum()

    city_context = {
        "service_type": target_service,
        "time_window": {
            "historical": "last_6_months",
            "live": "last_7_days"
        },
        "city_baselines": {
            "p50_hr": float(city_p50),
            "p90_hr": float(city_p90)
        },
        "service_volume": int(total_incidents)
    }

    # 3. Neighborhood-level Data
    # Merge fairness and signals
    merged = pd.merge(f_df, s_df, on="neighborhood", how="left", suffixes=('', '_sig'))
    
    neighborhoods_list = []
    
    for _, row in merged.iterrows():
        # Clean up signals (fill NaNs)
        backlog_p = row.get('backlog_pressure', 0.0)
        ratio_p90 = row.get('ratio_p90', 0.0)
        if pd.isna(backlog_p): backlog_p = 0.0
        
        # Compute severity_score
        severity = ratio_p90 * (1 + backlog_p)
        
        n_data = {
            "neighborhood": row['neighborhood'],
            "fairness_metrics": {
                "p50_hr": row['p50_hr'],
                "p90_hr": row['p90_hr'],
                "ratio_p90": ratio_p90,
                "rank": int(row['rank']) if pd.notna(row['rank']) else 0,
                "worst_k_flag": bool(row['worst_k_flag']) if pd.notna(row['worst_k_flag']) else False
            },
            "signals": {
                "backlog_pressure": backlog_p,
                "aging_tail_14d": row.get('aging_tail_14d', 0.0),
                "duplicate_rate": row.get('duplicate_rate', 0.0),
                "mislabel_rate": row.get('mislabel_rate', 0.0),
                "agency_fragmentation": row.get('agency_fragmentation') # can be None
            },
            "severity_score": float(severity)
        }
        neighborhoods_list.append(n_data)

    # 6. Derived Insights
    # Worst K
    worst_neighborhoods = [n['neighborhood'] for n in neighborhoods_list if n['fairness_metrics']['worst_k_flag']]
    
    # Priority (severity > median)
    severities = [n['severity_score'] for n in neighborhoods_list]
    median_severity = np.median(severities) if severities else 0
    priority_neighborhoods = [n['neighborhood'] for n in neighborhoods_list if n['severity_score'] > median_severity]
    
    # Overall Severity
    max_severity = max(severities) if severities else 0
    if max_severity < 1.5:
        overall = "low"
    elif max_severity <= 3.0:
        overall = "medium"
    else:
        overall = "high"

    derived_insights = {
        "worst_neighborhoods": worst_neighborhoods,
        "priority_neighborhoods": priority_neighborhoods,
        "overall_severity": overall
    }

    # 7. Final Output
    city_state = {
        "city_context": city_context,
        "neighborhoods": neighborhoods_list,
        "governance": GOVERNANCE,
        "policy_space": POLICY_SPACE,
        "derived_insights": derived_insights
    }

    # Write to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(city_state, f, indent=2)

    print(f"City State built for '{target_service}' with {len(neighborhoods_list)} neighborhoods.")
    print(f"Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
